# CogniDrive ☁️🔒

**Secure Serverless Storage with AI-Powered Insights**

CogniDrive is a cloud-native file storage application leveraging AWS Serverless architecture. It creates a secure environment where users can sign in (via Google or Email/Password), upload their files to a private S3 bucket, and receive AI-generated summaries of their documents using AWS Bedrock.

## 🚀 Features

*   **Secure Authentication**: powered by **AWS Cognito**. Supports:
    *   Social Sign-in (Google)
    *   Email/Password Sign-up with verification
*   **Private Storage**: Each user gets a dedicated folder in **Amazon S3** (`user-id/*`) secured by **IAM** and **Cognito Identity Pools**.
*   **AI Processing**:
    *   **AWS Textract**: Automatically extracts text from uploaded PDFs and images.
    *   **AWS Bedrock**: Summarizes the document content providing instant insights.
*   **Serverless Backend**: Built with **AWS CDK** (Python) using Lambda, DynamoDB, and Cognito.
*   **Modern Frontend**: React + Vite + TypeScript application (using AWS Amplify UI).

---

## 🏗️ Architecture

1.  **Auth**: Cognito User Pool & Identity Pool.
2.  **API/Backend**:
    *   `PostConfirmation` Lambda: Enhances user profile in DynamoDB after sign-up.
    *   `FileProcessor` Lambda: Triggered by S3 uploads to run Textract & Bedrock.
3.  **Storage**: S3 Bucket (CORS enabled for direct browser uploads).
4.  **Database**: DynamoDB (Users table).

---

## 🛠️ Prerequisites

*   [Python 3.9+](https://www.python.org/downloads/)
*   [Node.js 18+](https://nodejs.org/)
*   [AWS CLI](https://aws.amazon.com/cli/) (configured with `aws configure`)
*   [AWS CDK CLI](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) (`npm install -g aws-cdk`)

---

## 📦 Getting Started

### 1. Backend Setup (AWS CDK)

Navigate to the project root:

```bash
# 1. Create and activate virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Deploy the stack
# Note: You may need to update 'app.py' or 'aws_cognito_auth_stack.py' 
# with your specific Region or Google Auth credentials before deploying.
cdk deploy
```

> **Note**: After deployment, note the `UserPoolId`, `UserPoolClientId`, `IdentityPoolId`, and `BucketName` from the outputs. You will need these for the frontend.

### 2. Frontend Setup (React + Vite)

Navigate to the frontend directory:

```bash
cd amplify-vite-react-template

# 1. Install dependencies
npm install

# 2. Configure AWS Resources
# Update your src/aws-exports.js or configuration file with the values from the CDK deployment.
# (If using Amplify Gen 2 or manual config, ensure the Amplify.configure() call matches your resources)

# 3. Run the development server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🧪 Usage

1.  **Sign Up/Login**: Use the "Sign in with Google" button or create a new account.
2.  **Upload**: Select a PDF or text file to upload to your secure folder.
3.  **View Insights**: Wait for the AI to process your file and display the summary (check CloudWatch logs or your notification setup if UI integration is pending).

---

## 🛡️ Security

*   **Row-Level Access**: Users can only access objects starting with their own `IdentityID`.
*   **Least Privilege**: IAM roles for Lambda functions are scoped strictly to necessary resources.
*   **Resource Cleanup**: `cdk destroy` will remove all resources (excluding retained data if configured).

---

## 🗑️ Cleanup

To avoid incurring future charges, delete the resources:

```bash
cdk destroy
```
