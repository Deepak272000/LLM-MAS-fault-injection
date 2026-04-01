FROM golang:1.25-alpine AS builder
WORKDIR /src

# Copy everything in 'src' so local dependencies are available
COPY . .

# Change to the specific service directory to build
WORKDIR /src/checkout-agent
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -o /checkoutservice .
