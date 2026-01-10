# Pre-Pause/Resume Verification Checklist

## What Gets Destroyed (Ephemeral)
- ❌ EKS Cluster
- ❌ EC2 instances (node groups)
- ❌ Load Balancers (ALBs)
- ❌ Security Groups
- ❌ Running pods/containers

## What Persists (Permanent)
- ✅ S3 Buckets + data
- ✅ ECR Images
- ✅ EBS Volumes (ChromaDB data)
- ✅ AWS Secrets Manager secrets
- ✅ Terraform state (in S3)

---

## Pre-Pause Verification Steps

### 1. Verify S3 Documents Exist
```bash
aws s3 ls s3://llmops-rag-documents-prod/documents/ --recursive
```
**Expected**: Should show your uploaded Cricket PDF

### 2. Verify ECR Images Exist
```bash
aws ecr describe-images --repository-name llmops-rag-api --region ap-southeast-2
aws ecr describe-images --repository-name llmops-rag-frontend --region ap-southeast-2
```
**Expected**: Should show `latest` tag for both

### 3. Verify EBS Volume Data
```bash
# Check volume exists and is attached
aws ec2 describe-volumes --volume-ids vol-04cfdee3709c4d6ff --region ap-southeast-2

# Check ChromaDB has data (from inside pod)
kubectl exec -n prod vectordb-0 -- du -sh /chroma/data
```
**Expected**: Volume should have non-zero size

### 4. Verify AWS Secrets Exist
```bash
aws secretsmanager describe-secret --secret-id rag-api-secrets-prod --region ap-southeast-2
```
**Expected**: Secret exists and has recent `LastAccessedDate`

### 5. Document Current State
**Load Balancers** (will be destroyed):
- API: `k8s-prod-ragapiin-36b1d54c9c-2098232989.ap-southeast-2.elb.amazonaws.com`
- Frontend: `k8s-prod-ragfront-17c86ef174-1012989703.ap-southeast-2.elb.amazonaws.com`
- Grafana: `af7baa4b080e04552a12240cd208ddce-1837042401.ap-southeast-2.elb.amazonaws.com`

**Persistent Resources**:
- Documents S3: `llmops-rag-documents-prod`
- VectorDB Volume: `vol-04cfdee3709c4d6ff`
- API ECR: `152141418178.dkr.ecr.ap-southeast-2.amazonaws.com/llmops-rag-api:latest`
- Frontend ECR: `152141418178.dkr.ecr.ap-southeast-2.amazonaws.com/llmops-rag-frontend:latest`
- Secrets: `rag-api-secrets-prod`

### 6. Test a Final Query
```bash
# Make 1-2 queries to ensure everything works
# Open frontend and ask about cricket laws
# Should return citations from the PDF
```

### 7. Verify GitHub Secrets Are Set
- `API_URL` (will need to be updated after resume with new ALB URL)
- `S3_DOCUMENTS_BUCKET`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

---

## Post-Resume Verification Steps

### 1. Wait for Infrastructure
- `terraform apply` takes ~20-30 minutes
- All pods should be Running

### 2. Update GitHub Variables
New ALB URLs will be different. Update:
- `API_URL` in GitHub repository variables

### 3. Redeploy Applications
```bash
./scripts/deploy_to_eks.sh prod
```

### 4. Verify Data Persistence
- Query about cricket laws → Should return same citations (data persisted!)
- Check Grafana has historical metrics from before pause

### 5. Test End-to-End
- Upload a NEW document
- Query both old and new documents
- Verify costs tracked in Grafana

---

## Ready to Pause?

**Before running `terraform destroy`:**
- [ ] All verification steps above passed
- [ ] You've documented what will be destroyed
- [ ] You're prepared for ~30-40 minute downtime
- [ ] You have the EBS Volume ID saved: `vol-04cfdee3709c4d6ff`

**Command to pause:**
```bash
cd terraform/environments/prod
terraform destroy -auto-approve
```

**Expected destruction time**: ~5-10 minutes

**Command to resume:**
```bash
cd terraform/environments/prod
terraform apply -auto-approve
```

**Expected creation time**: ~20-30 minutes
