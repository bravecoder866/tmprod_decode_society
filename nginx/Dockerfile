# Copyright (c) 2024 Qu Zhi
# All Rights Reserved.

# This software is proprietary and confidential.
# Unauthorized copying, distribution, or modification of this software is strictly prohibited.


# Use the official Nginx image
FROM nginx:alpine

# Remove default config
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy the appropriate Nginx configuration 
COPY default.conf /etc/nginx/conf.d/default.conf

