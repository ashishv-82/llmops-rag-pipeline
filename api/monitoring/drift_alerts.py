import boto3
import os
from api.monitoring.drift_detector import drift_detector
import logging

logger = logging.getLogger(__name__)

# Initialize SNS client
# In a real environment, region should be configurable
aws_region = os.getenv('AWS_REGION', 'ap-southeast-2')
try:
    sns_client = boto3.client('sns', region_name=aws_region)
except Exception as e:
    logger.warning(f"Failed to initialize SNS client: {e}. alerts will be logged only.")
    sns_client = None

def check_and_alert_drift(domain: str, topic_arn: str = None) -> dict:
    """
    Check for drift and send SNS alert if detected and topic_arn is provided.
    
    Args:
        domain: Domain to check for drift
        topic_arn: AWS SNS Topic ARN to publish alert to (optional)
        
    Returns:
        Drift detection result dict
    """
    result = drift_detector.detect_drift(domain)
    
    if result.get('drift_detected'):
        message = f"""
Data Drift Detected for Domain: {domain}
----------------------------------------
P-value: {result['p_value']:.4f} (Significant shift)
Current Mean Query Length: {result['current_mean_length']:.2f} words
Previous Mean Query Length: {result['previous_mean_length']:.2f} words
Sample Sizes: Current={result['current_samples']}, Previous={result['previous_samples']}

Recommendation:
- Review recent query logs for changing user behavior.
- Evaluate if retrieval or prompt strategies need adjustment.
- Consider retraining embeddings if specific vocabulary has shifted.
        """
        
        logger.warning(message)
        
        if sns_client and topic_arn:
            try:
                sns_client.publish(
                    TopicArn=topic_arn,
                    Subject=f"[MLOps] Data Drift Alert - {domain}",
                    Message=message
                )
                result['alert_sent'] = True
            except Exception as e:
                logger.error(f"Failed to send SNS alert: {e}")
                result['alert_sent'] = False
                result['alert_error'] = str(e)
        else:
            result['alert_sent'] = False
            result['reason'] = "SNS Not Configured"
            
    return result
