#!/bin/sh
DOMAIN="suvitech.io.vn"
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

if [ ! -f "$CERT_PATH" ]; then
    echo "[1/3] Chưa có SSL. Chạy cấu hình HTTP mồi để chờ Certbot..."
    cp /etc/nginx/nginx-http.conf /etc/nginx/nginx.conf
    
    # Khởi động Nginx chạy ngầm để hứng request xác thực
    nginx -g "daemon off;" &
    NGINX_PID=$!

    echo "[2/3] Đang chờ Certbot lấy chứng chỉ về..."
    while [ ! -f "$CERT_PATH" ]; do
        sleep 2
    done

    echo "[3/3] Đã có SSL! Đổi sang cấu hình HTTPS và Reload..."
    cp /etc/nginx/nginx-https.conf /etc/nginx/nginx.conf
    nginx -s reload

    # Giữ container tiếp tục chạy
    wait $NGINX_PID
else
    echo "✅ Đã có sẵn SSL. Khởi động với cấu hình HTTPS hoàn chỉnh..."
    cp /etc/nginx/nginx-https.conf /etc/nginx/nginx.conf
    exec nginx -g "daemon off;"
fi