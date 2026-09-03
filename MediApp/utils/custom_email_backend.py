import smtplib
import ssl
from django.core.mail.backends.smtp import EmailBackend


class UnverifiedSMTPBackend(EmailBackend):
    """
    SMTP Email backend with SSL certificate verification bypass for Windows environments
    where local CA bundles or antivirus proxies cause CERTIFICATE_VERIFY_FAILED errors.
    """

    def open(self):
        if self.connection:
            return False

        if self._partial_connection is not None:
            self._close_connection(self._partial_connection)
            self._partial_connection = None

        connection_params = {}
        if self.timeout is not None:
            connection_params["timeout"] = self.timeout

        try:
            self._partial_connection = smtplib.SMTP(self.host, self.port, **connection_params)

            if self.use_tls:
                ctx = ssl._create_unverified_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                self._partial_connection.starttls(context=ctx)

            if self.username and self.password:
                clean_password = self.password.replace(" ", "") if isinstance(self.password, str) else self.password
                try:
                    self._partial_connection.login(self.username, self.password)
                except smtplib.SMTPAuthenticationError:
                    if clean_password != self.password:
                        self._partial_connection.login(self.username, clean_password)
                    else:
                        raise

            self.connection = self._partial_connection
            self._partial_connection = None
            return True
        except Exception:
            if not self.fail_silently:
                raise
