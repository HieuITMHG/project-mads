# AI-Powered E-Commerce Data Assistant (MADS)

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-Stateful_Agents-orange)
![Docker](https://img.shields.io/badge/Docker-Production_Ready-2496ED?logo=docker)
![Celery](https://img.shields.io/badge/Celery-Async_Tasks-37814A?logo=celery)

Một hệ thống AI Assistant Full-stack được thiết kế theo kiến trúc **Stateful Agentic Workflow** với nền tảng là ReAct pattern. Ứng dụng tích hợp các công nghệ tiên tiến về LLM và Data Engineering nhằm phân tích, truy vấn và trực quan hóa tập dữ liệu thương mại điện tử phức tạp, đồng thời đảm bảo tính bảo mật và kiểm soát chặt chẽ thông qua cơ chế Human-in-the-Loop.

## Điểm nổi bật (Key Features)

* **Stateful Agentic Workflow (LangGraph):** Đóng vai trò là Orchestrator điều phối các công việc phức tạp, tự động lên kế hoạch, gọi tool và tổng hợp kết quả.
* **Long-term Memory (Checkpointer):** Sử dụng LangGraph Checkpointer để lưu trữ toàn bộ context và trạng thái của các phiên trò chuyện, giúp Agent có khả năng "nhớ" ngữ cảnh dài hạn và cá nhân hóa trải nghiệm.
* **Secure Data Access (Read-only Query Tool):** Công cụ truy vấn Database (SQL Tool) được cấp quyền bằng một user `readonly` chuyên biệt trên PostgreSQL, ngăn chặn hoàn toàn rủi ro AI thực thi các lệnh xóa/sửa dữ liệu nguy hiểm.
* **Isolated Code Sandbox:** Môi trường thực thi code Python (để sinh biểu đồ, phân tích data) được cô lập hoàn toàn (Secure Sandbox), tránh rủi ro bảo mật cho hệ thống máy chủ chính.
* **MCP Server Integration:** Sử dụng **Model Context Protocol (MCP)** để chuẩn hóa việc phục vụ và giao tiếp các Tools cho LLM, giúp hệ thống dễ dàng mở rộng và tách biệt logic của tools khỏi core agent.
* **RAG Pipeline:** Xử lý tài liệu và văn bản phức tạp với **Docling**, kết hợp cùng Vector Database để truy xuất thông tin ngữ cảnh chính xác cao.
* **Asynchronous Processing:** Sử dụng **Celery + Redis** để xử lý các tác vụ nặng (Data Ingestion, nhúng vector) dưới background mà không chặn luồng chính của API.
* **Human-in-the-Loop (HITL):** Tích hợp cơ chế phê duyệt của con người trước khi Agent thực thi các tác vụ nhạy cảm hoặc tiêu tốn tài nguyên lớn.

## Tech Stack

* **Backend:** FastAPI, Python, Celery, Redis
* **AI / Orchestration:** LangChain, LangGraph, Model Context Protocol (MCP)
* **Data / RAG:** PostgreSQL, Qdrant (Vector DB), MinIO (Object Storage), Docling (Parsing)
* **Infrastructure:** Docker, Docker Compose, Nginx, Let's Encrypt (Certbot)
* **Frontend:** ReactJS / Vite (Này mình vibe code =>)

## Dataset: Olist E-Commerce
Hệ thống được thiết kế để phân tích tập dữ liệu **Olist** (Brazilian E-Commerce Public Dataset). Đây là một tập dữ liệu thực tế lớn bao gồm thông tin về:
* Hơn 100,000 đơn hàng từ năm 2016 đến 2018.
* Chi tiết sản phẩm, khách hàng, đánh giá (reviews), vị trí địa lý và các luồng thanh toán.
* **Thử thách giải quyết:** Agent phải hiểu được Schema cơ sở dữ liệu quan hệ phức tạp này để tự động viết SQL, tổng hợp báo cáo và trả lời các câu hỏi kinh doanh của người dùng.

---

## Demo & Screenshots

### 1. Giao diện Chat & Trực quan hóa dữ liệu
![Giao diện chính]
<p align="center">
  <img src="./assets/chart_res.png" alt="Chatbot Demo">
</p>
*Người dùng yêu cầu báo cáo doanh thu, Agent tự động viết SQL, lấy data và viết code sinh biểu đồ ngay trên giao diện.*

### 2. Luồng Human-in-the-Loop (HITL)
![HITL Demo1]
<p align="center">
  <img src="./assets/HIL1.png" alt="Chatbot Demo">
</p>
---
<p align="center">
  <img src="./assets/HIL2.png" alt="Chatbot Demo">
</p>
---
<p align="center">
  <img src="./assets/chart_res2.png" alt="Chatbot Demo">
</p>

*Hệ thống tạm dừng và yêu cầu người dùng xác nhận trước khi cho phép Agent thực thi một đoạn mã phân tích phức tạp.*

## Hướng dẫn triển khai (Deployment)

Dự án được đóng gói hoàn toàn bằng Docker, giúp việc triển khai lên môi trường Production (hoặc chạy Local).

### Bước 1: Clone Repository
```bash
git clone https://github.com/HieuITMHG/project-mads.git
cd project-mads
```

### Bước 2: 

Bạn sẽ cần một tài khoản kaggle để tải và ingest Olist dataset về. Mở file .env.prod và sửa

* KAGGLE_USERNAME=your_kaggle_username
* KAGGLE_KEY=your_kaggle_key

Mình sử dụng API của OpenAI cho phần LLM

* OPENAI_API_KEY=your_api_key

Mở file frontend/.env.production sửa 

* VITE_API_URL=https://<your-domain>/api

### Bước 3:

Chạy lệnh sau để build image cho Sandbox

```bash
docker build -t mads-sandbox-base -f infras/docker/Dockerfile.sandbox .
```

### Bước 4:
Build project

```bash
make build ENV=prod
```

### Bước 5:
```bash
make up ENV=prod
```

Bạn đã có thể truy cập domain của mình.

---

## Các vấn đề hiện tại

* Do mình sử dụng mình sử dụng Openai API nên không thể để user vào demo và spam hết token được, do đó app sẽ không có phần đăng ký người dùng trên giao diện, và phần hướng dẫn desploy chỉ để tham khảo và hoàn toàn không nên để web chạy lâu dài, sau khi demo xong nên xóa ngay. Bạn có thể tạo demo user bằng cách

```bash
curl.exe -X POST "https://suvitech.io.vn/api/register" `
  -H "accept: application/json" `
  -H "Content-Type: application/json" `
  --data-raw '{\"username\":\"your_user_name\",\"password\":\"123456\"}'
```

Người khác có thể tạo user bằng cách tương tự và spam hết token của bạn.





