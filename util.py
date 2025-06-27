def s3_to_url(s3_uri: str, region: str = "us-east-2") -> str:
    if s3_uri.startswith("s3://"):
        parts = s3_uri[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
    return s3_uri