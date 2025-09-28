#!/bin/bash

echo "🚀 Starting VibeSDLC Microservices..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please update .env with your API keys before proceeding."
    exit 1
fi

# Start infrastructure services first
echo "🔧 Starting infrastructure services..."
docker-compose up -d postgres zookeeper kafka

# Wait for Kafka to be ready
echo "⏳ Waiting for Kafka to be ready..."
sleep 30

# Create Kafka topics
echo "📝 Creating Kafka topics..."
docker-compose exec kafka kafka-topics --create --topic user-events --bootstrap-server localhost:29092 --partitions 3 --replication-factor 1 --if-not-exists
docker-compose exec kafka kafka-topics --create --topic item-events --bootstrap-server localhost:29092 --partitions 3 --replication-factor 1 --if-not-exists
docker-compose exec kafka kafka-topics --create --topic agent-events --bootstrap-server localhost:29092 --partitions 3 --replication-factor 1 --if-not-exists

# Start application services
echo "🏗️  Starting application services..."
docker-compose up -d management-service ai-agent-service

# Start frontend
echo "🎨 Starting frontend..."
docker-compose up -d frontend

# Start monitoring
echo "📊 Starting monitoring services..."
docker-compose up -d kafka-ui

echo "✅ All services started successfully!"
echo ""
echo "🌐 Access URLs:"
echo "   Frontend:           http://localhost:5173"
echo "   Management Service: http://localhost:8000"
echo "   AI Agent Service:   http://localhost:8001"
echo "   Kafka UI:          http://localhost:8080"
echo ""
echo "📋 To view logs: docker-compose logs -f [service-name]"
echo "🛑 To stop all:  docker-compose down"