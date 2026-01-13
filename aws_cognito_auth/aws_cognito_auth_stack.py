from aws_cdk import (
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_iam as iam,
    aws_s3_notifications as s3n,
    Duration
    
)
from constructs import Construct

class MyAuthAppStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ==================================================
        # 1. DynamoDB Table (To store user logs/details)
        # ==================================================
        user_table = dynamodb.Table(
            self, "AppUserTable",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY, # NOT for production
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        # ==================================================
        # 2. Lambda Trigger (Post Confirmation)
        # ==================================================
        post_confirmation_fn = _lambda.Function(
            self, "PostConfirmationHandler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="post_confirmation.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "USER_TABLE_NAME": user_table.table_name
            }
        )

        # Grant the Lambda permission to write to the table
        user_table.grant_write_data(post_confirmation_fn)

        # ==================================================
        # 3. Cognito User Pool
        # ==================================================
        user_pool = cognito.UserPool(
            self, "MyUserPool",
            self_sign_up_enabled=True,
            
            # Login options (Username or Email)
            sign_in_aliases=cognito.SignInAliases(
                username=True,
                email=True
            ),
            
            # Attributes required from the user
            standard_attributes=cognito.StandardAttributes(
                fullname=cognito.StandardAttribute(required=True, mutable=True),
                email=cognito.StandardAttribute(required=True, mutable=True),
            ),

            # Password Policy
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_digits=True,
                require_uppercase=True,
                require_symbols=False
            ),

            # Account Recovery (This handles the "Reset Password" requirement)
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            
            # Attach the Lambda Trigger created above
            lambda_triggers=cognito.UserPoolTriggers(
                post_confirmation=post_confirmation_fn
            )
        )

        # ==================================================
        # 4. Google Identity Provider Setup
        # ==================================================
        # NOTE: In production, pull these from SecretsManager or Context
        google_client_id = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        google_client_secret = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

        google_provider = cognito.UserPoolIdentityProviderGoogle(
            self, "GoogleProvider",
            user_pool=user_pool,
            client_id=google_client_id,
            client_secret=google_client_secret,
            # Map Google attributes to Cognito attributes
            attribute_mapping=cognito.AttributeMapping(
                email=cognito.ProviderAttribute.GOOGLE_EMAIL,
                fullname=cognito.ProviderAttribute.GOOGLE_NAME,
                profile_picture=cognito.ProviderAttribute.GOOGLE_PICTURE
            ),
            scopes=["profile", "email", "openid"]
        )

        # ==================================================
        # 5. User Pool Client (App Client)
        # ==================================================
        user_pool_client = user_pool.add_client(
            "WebAppClient",
            user_pool_client_name="MyWebAppClient",
            generate_secret=False, # True for backend apps, False for frontend (SPA/Mobile)
            
            # Allow both Google and standard Cognito (User/Pass) flows
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.GOOGLE,
                cognito.UserPoolClientIdentityProvider.COGNITO
            ],

            # OAuth Configuration (Crucial for Google Sign-in)
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=True 
                ),
                scopes=[
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE
                ],
                # Must match exactly what is in Google Console Authorized Redirect URIs
                callback_urls=["http://localhost:5173/"],
                logout_urls=["http://localhost:5173/"]
            )
        )

        # Ensure Google provider is created before the client tries to use it
        user_pool_client.node.add_dependency(google_provider)

        # ==================================================
        # 6. User Pool Domain (Required for Social Auth)
        # ==================================================
        # This creates https://<your-prefix>.auth.<region>.amazoncognito.com
        user_pool.add_domain(
            "CognitoDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix="auth-app-vedant-2026-test" # Must be globally unique
            )
        )

        # ==================================================
        # 7. S3 Bucket for User Files
        # ==================================================
        file_bucket = s3.Bucket(
            self, "UserFileBucket",
            removal_policy=RemovalPolicy.DESTROY, # NOT for production
            auto_delete_objects=True,
            cors=[s3.CorsRule(
                allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST, s3.HttpMethods.DELETE, s3.HttpMethods.HEAD],
                allowed_origins=["*"], # In production, restrict to your domain like "http://localhost:5173"
                allowed_headers=["*"]
            )]
        )

        # ==================================================
        # 8. Identity Pool (The bridge for AWS Permissions)
        # ==================================================
        identity_pool = cognito.CfnIdentityPool(
            self, "MyIdentityPool",
            allow_unauthenticated_identities=False,
            cognito_identity_providers=[
                cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
                    client_id=user_pool_client.user_pool_client_id,
                    provider_name=user_pool.user_pool_provider_name
                )
            ]
        )

        # ==================================================
        # 9. IAM Role for Authenticated Users
        # ==================================================
        # This role defines what a logged-in user is allowed to do
        auth_role = iam.Role(
            self, "CognitoDefaultAuthenticatedRole",
            assumed_by=iam.FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                {
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": identity_pool.ref
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated"
                    }
                },
                "sts:AssumeRoleWithWebIdentity"
            )
        )

        # Policy: Allow user to upload ONLY to their own folder: bucket/user-id/*
        auth_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket"],
            resources=[
                file_bucket.bucket_arn,
                f"{file_bucket.bucket_arn}/*" # Allow access to all files (we control path in frontend)
            ]
        ))

        # Attach role to Identity Pool
        cognito.CfnIdentityPoolRoleAttachment(
            self, "IdentityPoolRoleAttachment",
            identity_pool_id=identity_pool.ref,
            roles={
                "authenticated": auth_role.role_arn
            }
        )

        # ==================================================
        # 10. Outputs
        # ==================================================
        CfnOutput(self, "BucketName", value=file_bucket.bucket_name)
        CfnOutput(self, "IdentityPoolId", value=identity_pool.ref)

        # ==================================================
        # 11. File Processor Lambda (AI Summarizer)
        # ==================================================

        processor_fn = _lambda.Function(
            self, "FileProcessorHandler",
            runtime=_lambda.Runtime.PYTHON_3_12, # <--- CRITICAL UPDATE
            handler="process_file.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(60),        # <--- Ensure this is 60s (AI takes time)
            environment={
                "BEDROCK_MODEL_ID": "amazon.titan-text-express-v1"
            }
        )

        # Permissions: Read/Write S3
        file_bucket.grant_read_write(processor_fn)

        # Permissions: Allow using Textract (for extracting text from PDFs)
        processor_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["textract:DetectDocumentText"],
            resources=["*"]
        ))

        # Permissions: Allow using Bedrock (for generating summaries)
        processor_fn.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"]
        ))

        # ==================================================
        # 12. Connect S3 Event to Lambda
        # ==================================================
        # When a file is created, run the Lambda
        file_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(processor_fn),
            # Optional: Filter to only process PDFs or Text files if you want
            # s3.NotificationKeyFilter(suffix=".pdf") 
        )