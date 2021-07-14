"""Custom file storage classes."""
from storages.backends.s3boto3 import S3Boto3Storage


class S3Boto3CustomStorage(S3Boto3Storage):
    """Override some upload parameters, such as ContentDisposition header."""

    def _get_write_parameters(self, name, content):
        """Set ContentDisposition header using original file name.

        While docstring recommends overriding `get_object_parameters` for this purpose,
        `get_object_parameters` only gets a `name` which is not the original file name,
        but the result of `upload_to`.
        """
        params = super()._get_write_parameters(name, content)
        original_name = getattr(content, 'name', None)
        if original_name and name != original_name:
            content_disposition = f'attachment; filename="{original_name}"'
            params['ContentDisposition'] = content_disposition
        return params
