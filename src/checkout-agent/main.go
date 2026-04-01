package main

import (
	"context"
	"fmt"
	"net"
	"os"
	"time"

	"checkoutservice-agent/agent"
	pb "checkoutservice-agent/genproto"
	"github.com/sirupsen/logrus"
	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"
	"google.golang.org/grpc/status"
)

const (
	listenPort = "5050"
)

var log *logrus.Logger

func init() {
	log = logrus.New()
	log.Level = logrus.DebugLevel
	log.Formatter = &logrus.JSONFormatter{
		FieldMap: logrus.FieldMap{
			logrus.FieldKeyTime:  "timestamp",
			logrus.FieldKeyLevel: "severity",
			logrus.FieldKeyMsg:   "message",
		},
		TimestampFormat: time.RFC3339Nano,
	}
	log.Out = os.Stdout
}

// checkoutServiceServer wraps the agent and implements the gRPC server interface.
type checkoutServiceServer struct {
	pb.UnimplementedCheckoutServiceServer
	agent *agent.CheckoutAgent
}

func (s *checkoutServiceServer) Check(_ context.Context, _ *healthpb.HealthCheckRequest) (*healthpb.HealthCheckResponse, error) {
	return &healthpb.HealthCheckResponse{Status: healthpb.HealthCheckResponse_SERVING}, nil
}

func (s *checkoutServiceServer) Watch(_ *healthpb.HealthCheckRequest, _ healthpb.Health_WatchServer) error {
	return status.Errorf(codes.Unimplemented, "health check via Watch not implemented")
}

func (s *checkoutServiceServer) List(_ context.Context, _ *healthpb.HealthListRequest) (*healthpb.HealthListResponse, error) {
	return &healthpb.HealthListResponse{}, nil
}

func (s *checkoutServiceServer) PlaceOrder(ctx context.Context, req *pb.PlaceOrderRequest) (*pb.PlaceOrderResponse, error) {
	log.Infof("[PlaceOrder] user_id=%q user_currency=%q", req.UserId, req.UserCurrency)
	return s.agent.PlaceOrder(ctx, req)
}

func mustGetEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	// Downstream service addresses
	cfg := agent.Config{
		CartSvcAddr:        mustGetEnv("CART_SERVICE_ADDR", "cartservice:7070"),
		ProductCatalogAddr: mustGetEnv("PRODUCT_CATALOG_SERVICE_ADDR", "productcatalogservice:3550"),
		CurrencySvcAddr:    mustGetEnv("CURRENCY_SERVICE_ADDR", "currencyservice:7000"),
		ShippingSvcAddr:    mustGetEnv("SHIPPING_SERVICE_ADDR", "shippingservice:50051"),
		PaymentSvcAddr:     mustGetEnv("PAYMENT_SERVICE_ADDR", "paymentservice:50051"),
		EmailSvcAddr:       mustGetEnv("EMAIL_SERVICE_ADDR", "emailservice:8080"),
		OllamaAddr:         mustGetEnv("OLLAMA_ADDR", "http://ollama:11434"),
		OllamaModel:        mustGetEnv("OLLAMA_MODEL", "llama3.2:1b"),
	}

	checkoutAgent, err := agent.New(cfg, log)
	if err != nil {
		log.Fatalf("failed to create checkout agent: %v", err)
	}
	defer checkoutAgent.Close()

	lis, err := net.Listen("tcp", fmt.Sprintf(":%s", listenPort))
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	srv := grpc.NewServer(
		grpc.StatsHandler(otelgrpc.NewServerHandler()),
	)

	svc := &checkoutServiceServer{agent: checkoutAgent}
	pb.RegisterCheckoutServiceServer(srv, svc)
	healthpb.RegisterHealthServer(srv, svc)
	reflection.Register(srv)

	log.Infof("starting gRPC server on :%s (agent mode, ollama=%s, model=%s)",
		listenPort, cfg.OllamaAddr, cfg.OllamaModel)

	if err := srv.Serve(lis); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}
