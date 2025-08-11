# SecureShare
SecureShare is a platform for secure file sharing with temporary access.

[Core Features]:

- Temporary File Sharing: Users can upload files and generate unique download links that expire after a specified time (e.g., 24 hours).

- Simple Full-Text Search: Users can search previously uploaded files in their personal account using keywords or file names.

- User Registration and Authentication: Simple sign-up with username/password authentication, plus optional two-factor authentication (2FA) for enhanced security.

- Custom Link Expiration: Users can set link expiration periods (e.g., 1, 3, 7 days, up to two weeks). After expiration, file access is disabled.

- Personal Dashboard: View uploaded files, track active links, and delete files as needed.

- Download Reports: Notifications showing when a file was downloaded, the originating IP address, and basic download statistics (e.g., total downloads).

[Killer Feature]:

- Automatic Cleanup of Inactive Links: After a link expires (based on time or a download limit set by the link creator), the system automatically deletes the file and notifies the user. Users are also proactively notified before the link expires, allowing them to extend its validity period if desired.
