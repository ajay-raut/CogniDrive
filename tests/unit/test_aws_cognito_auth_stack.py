import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_cognito_auth.aws_cognito_auth_stack import AwsCognitoAuthStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_cognito_auth/aws_cognito_auth_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsCognitoAuthStack(app, "aws-cognito-auth")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
