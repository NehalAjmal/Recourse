<div align="center">
  <h1>🛡️ Recourse</h1>
  <p>
    <img src="https://img.shields.io/badge/Built%20on-AWS-232F3E?logo=amazonaws&logoColor=white" alt="Built on AWS" />
    <img src="https://img.shields.io/badge/Bharat%20Builds%20Tour-First%20Commit-1a1a2e" alt="Bharat Builds Tour" /><br>
    <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB" alt="React" />
    <img src="https://img.shields.io/badge/TypeScript-007ACC?logo=typescript&logoColor=white" alt="TypeScript" />
    <img src="https://img.shields.io/badge/Tailwind_CSS-38B2AC?logo=tailwind-css&logoColor=white" alt="Tailwind CSS" />
    <img src="https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white" alt="Vite" />
    <img src="https://img.shields.io/badge/Node.js-339933?logo=nodedotjs&logoColor=white" alt="Node.js" /><br>
    <img src="https://img.shields.io/badge/AWS_Lambda-FF9900?logo=aws-lambda&logoColor=white" alt="AWS Lambda" />
    <img src="https://img.shields.io/badge/Amazon_DynamoDB-4053D6?logo=amazon-dynamodb&logoColor=white" alt="Amazon DynamoDB" />
    <img src="https://img.shields.io/badge/Amazon_API_Gateway-FF4F8B?logo=amazon-api-gateway&logoColor=white" alt="Amazon API Gateway" />
    <img src="https://img.shields.io/badge/Amazon_Verified_Permissions-CC2222?logo=amazonaws&logoColor=white" alt="Amazon Verified Permissions" /><br>
    <img src="https://img.shields.io/badge/AWS_Amplify-E7157B?logo=aws-amplify&logoColor=white" alt="AWS Amplify" />
    <img src="https://img.shields.io/badge/AWS_SAM-232F3E?logo=amazonaws&logoColor=white" alt="AWS SAM" />
    <img src="https://img.shields.io/badge/Amazon_Bedrock-01A88D?logo=amazonaws&logoColor=white" alt="Amazon Bedrock" />
    <img src="https://img.shields.io/badge/Groq-F37021?logo=groq&logoColor=white" alt="Groq" />
  </p>
  <p><b>Evidence for disputes an AI agent made on your behalf.</b></p>
</div>

---

## 🔍 The Problem

In February 2026, Razorpay and NPCI launched an agentic payments pilot on Claude, letting people order from Zomato, Swiggy, and Zepto through conversation, using **UPI Reserve Pay** — a user pre-authorises a spending cap for a merchant, then an agent transacts within it.

> [!WARNING]  
> When one of those transactions is disputed, the evidence a merchant normally relies on doesn't exist: **no device fingerprint, no click trail, no browser session**, because no human clicked anything. Nothing off-the-shelf handles that yet.

---

## 🚫 What This Is Not

Recourse doesn't integrate with real UPI, Razorpay, or NPCI — every dispute is synthetic, shaped like the real thing. 

- **No login:** It's a demo console, not a product.
- **No simulation:** It doesn't build or simulate the shopping agent itself; it only consumes an agent's action log after the fact.

---

## 🧠 How It Decides

Every dispute goes through **six deterministic checks**. 

1. **Cedar Policies** (Evaluated by Amazon Verified Permissions):
   - Spending cap
   - Merchant match
   - Mandate validity window
2. **Python Checks**:
   - Order fulfilment
   - Timeline consistency
   - Duplicate-order detection

> [!IMPORTANT]  
> **The model never decides anything. It writes prose.**  
> Deterministic code decides whether that prose is trustworthy enough to show a human.

If all six pass, a language model writes a short evidence narrative. But the narrative is checked against the same structured facts before it's ever shown to anyone. If it mentions something structurally impossible for an agent-initiated transaction (a device fingerprint, an IP address, a click), or cites a number that appears nowhere in the real data, it's rejected and the dispute escalates to a human instead. 

**One generation attempt, no retries** — a failed check means escalation, never a second try hoping for a better answer.

---

## 🏗️ Architecture

```mermaid
graph TD
    A[POST /disputes] --> B(Ingest)
    B --> C{Evaluate}
    C -->|Cedar via AVP + Python checks| D
    D -->|Only if all 6 pass| E(Narrate: LLM call + Grounding check)
    E --> F[(DynamoDB)]
    C -.-> F
    
    subgraph Note
    N[Append-only audit trail at every transition]
    end
```

- **Backend:** Python 3.12 on AWS Lambda, Amazon Verified Permissions for policy evaluation, DynamoDB for storage, API Gateway as the HTTP front door, all declared in one AWS SAM template. 
- **Frontend:** React, TypeScript, Tailwind, deployed on AWS Amplify Hosting.

### ☁️ AWS Services Used

- **AWS Lambda** — all four backend services (ingest, evaluate, narrate, api)
- **Amazon Verified Permissions** — Cedar policy evaluation for 3 of the 6 checks (spending cap, merchant match, mandate validity window), declared as `AWS::VerifiedPermissions::PolicyStore` and `::Policy` resources directly in the SAM template — no separate console step
- **Amazon DynamoDB** — single-table store for mandates, disputes, and the append-only audit trail
- **Amazon API Gateway** — the HTTP front door for all endpoints
- **AWS Amplify Hosting** — deploys the React dashboard, `master.d285ptzirlim8s.amplifyapp.com`
- **AWS SAM** — declares and deploys the entire stack above from one `template.yaml`
- **Amazon Bedrock** — the narration step's original design target; blocked mid-build by an account-eligibility hold (see Limitations below), the code path is provider-agnostic and swaps back with a config change once access clears

---

## 🚀 Running It Locally

### Prerequisites
- Python 3.12, Node 20
- AWS CLI, AWS SAM CLI
- AWS account configured with `AdministratorAccess` credentials

### 1. Setup & Backend Deployment
```bash
git clone <repo-url> && cd recourse

# Setup Python virtual environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt --break-system-packages

# Run backend tests
pytest

# Build and deploy the AWS SAM stack
cd infra && sam build && sam deploy --guided 
```
> Take note of the `ApiUrl` output from the deployment.

### 2. Run the Frontend
```bash
cd ../web
npm install

# Start the dev server
VITE_API_URL=<api-url-from-above> npm run dev
```

### 3. Seed the Dataset
The seed dataset (120 synthetic disputes, 100 live + 20 held out with labels) is generated by `data/seed/generate_dataset.py` and posted to the deployed API.

```bash
cd data/seed
export API_URL="<api-url-from-above>"
python3 generate_dataset.py
```

---

## 🌐 Live Demo

- **App:** [https://master.d285ptzirlim8s.amplifyapp.com](https://master.d285ptzirlim8s.amplifyapp.com)
- **API:** [https://63v98k3fpe.execute-api.us-east-1.amazonaws.com/prod/disputes](https://63v98k3fpe.execute-api.us-east-1.amazonaws.com/prod/disputes)

---

## 📝 Limitations, honestly

> [!NOTE]  
> - **All data is synthetic.** This has never touched a real payment.
> - **No authentication anywhere** — a deliberate scope decision for a four-day demo, not an oversight.
> - **Bedrock access** was blocked for the account this was built on by an AWS account-verification hold that didn't clear in time. The `narrate` service calls a free-tier LLM API directly instead — the decision logic and grounding check are provider-agnostic and don't change based on which model writes the prose.
> - A small number of early audit-log entries had their display order reconstructed after a same-second timestamp collision, caused by rapid manual testing during development. Entries written from that point forward use microsecond-precision sort keys and don't have this issue.
> - Precision and recall on the held-out set are both **1.0**. This is a deterministic rule engine evaluated against synthetic cases with unambiguous ground truth, not a trained model generalising to unseen data — a correctly implemented deterministic system is expected to score close to perfect on clean-cut cases. It isn't a claim that the system is infallible on messier real data.

---

## 🏆 Built For

**Bharat Builds Tour — First Commit**  
WeMakeDevs × AWS Builder Center, 17–20 September 2026.
