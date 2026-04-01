FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Generate gRPC stubs
RUN python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. ./proto/hipstershop.proto

EXPOSE 3550
CMD ["python", "server.py"]