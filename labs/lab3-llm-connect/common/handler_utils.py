import urllib.parse


def parse_s3_event(event):
    records = event.data.get('Records') or event.data.get('data', {}).get('Records', [])
    if not records:
        return None, None
    bucket = records[0]['s3']['bucket']['name']
    key = urllib.parse.unquote(records[0]['s3']['object']['key'])
    return bucket, key
