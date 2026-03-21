import mimetypes
import uuid
import urllib.request


def _encode_multipart_form_data(fields, files):
    boundary = f'----NoOneIsSafeBoundary{uuid.uuid4().hex}'
    body = bytearray()
    for field_name, value in fields.items():
        if value is None:
            continue
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        disposition = f'Content-Disposition: form-data; name="{field_name}"'
        body.extend(f'{disposition}\r\n\r\n'.encode('utf-8'))
        body.extend(str(value).encode('utf-8'))
        body.extend(b'\r\n')
    for field_name, file_path in files:
        mime_type = mimetypes.guess_type(file_path.name)[0]
        if mime_type is None:
            mime_type = 'application/octet-stream'
        with file_path.open('rb') as file_handle:
            payload = file_handle.read()
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        disposition = (
            f'Content-Disposition: form-data; name="{field_name}"; '
            f'filename="{file_path.name}"'
        )
        body.extend(f'{disposition}\r\n'.encode('utf-8'))
        body.extend(f'Content-Type: {mime_type}\r\n\r\n'.encode('utf-8'))
        body.extend(payload)
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
    content_type = f'multipart/form-data; boundary={boundary}'
    return bytes(body), content_type


def post_multipart(url, fields, files, timeout):
    body, content_type = _encode_multipart_form_data(fields, files)
    request = urllib.request.Request(
        url,
        data=body,
        headers={'Content-Type': content_type},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status

