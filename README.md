# Recourse

Recourse gives a merchant's dispute team the evidence they would normally lose when an AI agent makes a purchase.

When a transaction is made by an agent via a pre-authorized spending cap (like UPI Reserve Pay), traditional dispute evidence does not exist. There is no device fingerprint, no click trail, and no browser session because no human clicked anything. Recourse replaces that missing evidence with a verifiable chain of facts: what the user authorized, what the agent executed, and whether the order was fulfilled.

Existing dispute tooling assumes human operators. Attempting to solve this problem by asking a large language model to read logs and decide the outcome introduces a new risk. Models can hallucinate justifications or rubber-stamp agent behavior based on probabilistic generation, making their decisions legally and operationally indefensible.

## How it works

Recourse separates the decision path from the narrative generation. 

The system relies on Amazon Verified Permissions (using the Cedar policy language) and deterministic Python checks to evaluate the facts of a dispute. The evaluation pipeline checks the mandate validity, the spend cap limit, and the fulfillment status. If the facts pass all checks, the dispute is marked as contested. If it fails slightly, it escalates to a human analyst. If it fails severely, the dispute is accepted and resolved.

Only after a deterministic decision is made does the system call a generative model (Amazon Bedrock) to write a human-readable narrative. This narrative is then subjected to a strict grounding check. If the generated text invents numbers, references facts that do not exist in the evidence, or violates length constraints, the narrative is discarded and the dispute escalates. A model never makes a decision, and it is never trusted to verify its own work.

## Limitations

This is a prototype built for demonstration purposes. It contains several deliberate limitations.

The application uses deterministic synthetic data generated via a seed, rather than a live database of real transactions. The dashboard is entirely read-only. There is no functionality to manually override a decision, approve an escalation, or edit a narrative. There is no user authentication, session management, or role-based access control implemented on the frontend. The system does not implement a full component library or dark mode, favoring a minimal console interface. Finally, only one foundation model attempt is made per dispute to control costs and prevent silent retry loops from burying hallucination failures.

## Local setup and deployment

To run the backend infrastructure locally, you need the AWS CLI, AWS SAM CLI, Python 3.12, and Node 20. You must have an AWS account configured with AdministratorAccess credentials in your local environment.

First, build and deploy the AWS SAM stack:

```bash
cd infra
sam build
sam deploy --guided
```

This provisions the DynamoDB tables, the API Gateway endpoints, the Lambda functions, and the Amazon Verified Permissions policy store. Take note of the `ApiUrl` output from the deployment.

Next, seed the database with synthetic dispute data:

```bash
cd data/seed
python generate_dataset.py
```

Finally, run the frontend dashboard locally:

```bash
cd web
npm install
# Set VITE_API_URL in your environment to the ApiUrl from the SAM deploy
VITE_API_URL="https://your-api-id.execute-api.us-east-1.amazonaws.com/prod" npm run dev
```

The dashboard will be available at `http://localhost:5173`.