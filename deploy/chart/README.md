# Vestaboard MQTT Bridge Helm Chart

Helm chart for deploying the Vestaboard MQTT Bridge application to Kubernetes.

## Features

- ✅ Multi-Vestaboard support with configurable topic prefixes
- ✅ Secure MQTT with TLS/SSL and mutual TLS support
- ✅ External Secrets integration for sensitive data
- ✅ Last Will and Testament (LWT) for connection monitoring
- ✅ Configurable QoS levels and connection settings
- ✅ Health checks and readiness probes
- ✅ Horizontal Pod Autoscaling support
- ✅ Support for both Cloud and Local Vestaboard APIs
- ✅ Multi-board type support (Standard 6x22, Note 3x15)

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- External Secrets Operator (if using external secrets)
- MQTT broker (Mosquitto, HiveMQ, AWS IoT, etc.)

## Installation

### Quick Start

```bash
# Add the repository (if published to a Helm repo)
helm repo add vestaboard-mqtt https://your-repo-url

# Install with default values
helm install vestaboard-mqtt vestaboard-mqtt/vestaboard-mqtt \
  --set mqtt.broker.host=mqtt.example.com \
  --set mqtt.broker.port=1883

# Or install from local chart
helm install vestaboard-mqtt ./deploy/chart \
  --set mqtt.broker.host=mqtt.example.com
```

### Install with Custom Values

```bash
# Create your custom values file
cat > my-values.yaml <<EOF
mqtt:
  broker:
    host: "mqtt.home.local"
    port: "1883"
  topicPrefix: "vestaboard"

vestaboard:
  boardType: "standard"
EOF

# Install with custom values
helm install vestaboard-mqtt ./deploy/chart -f my-values.yaml
```

## Configuration

### MQTT Configuration

#### Basic Connection

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mqtt.broker.host` | MQTT broker hostname | `localhost` |
| `mqtt.broker.port` | MQTT broker port | `1883` |
| `mqtt.topicPrefix` | Topic prefix for all MQTT topics | `vestaboard` |

#### Connection Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mqtt.connection.clientId` | MQTT client ID (empty for auto-generate) | `""` |
| `mqtt.connection.cleanSession` | Clean session on reconnect | `"true"` |
| `mqtt.connection.keepalive` | Keep-alive interval in seconds | `"60"` |
| `mqtt.connection.qos` | Default QoS level (0, 1, or 2) | `"0"` |

#### TLS/SSL Security

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mqtt.tls.enabled` | Enable TLS/SSL encryption | `false` |
| `mqtt.tls.caCerts` | Path to CA certificate file | `""` |
| `mqtt.tls.certFile` | Path to client certificate (mutual TLS) | `""` |
| `mqtt.tls.keyFile` | Path to client key (mutual TLS) | `""` |
| `mqtt.tls.insecure` | Skip certificate verification (testing only) | `"false"` |

#### Last Will & Testament

| Parameter | Description | Default |
|-----------|-------------|---------|
| `mqtt.lwt.enabled` | Enable Last Will and Testament | `false` |
| `mqtt.lwt.topic` | LWT topic | `""` |
| `mqtt.lwt.payload` | LWT message payload | `"offline"` |
| `mqtt.lwt.qos` | LWT QoS level | `"0"` |
| `mqtt.lwt.retain` | Retain LWT message | `"true"` |

### Vestaboard Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `vestaboard.useLocalApi` | Use Local API instead of Cloud API | `false` |
| `vestaboard.boardType` | Board type: `standard`, `note`, or `rows,cols` | `"standard"` |
| `vestaboard.localApi.host` | Local API hostname (if useLocalApi=true) | `"vestaboard.local"` |
| `vestaboard.localApi.port` | Local API port (if useLocalApi=true) | `"7000"` |
| `vestaboard.cloudApi.secretKeyPath` | External secret path for Cloud API key | `"vestaboard-mqtt/api"` |
| `vestaboard.localApiSecret.secretKeyPath` | External secret path for Local API key | `"vestaboard-mqtt/local-api"` |

### Application Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `application.httpPort` | HTTP API port | `"8000"` |
| `application.logLevel` | Logging level (DEBUG, INFO, WARNING, ERROR) | `"INFO"` |

### External Secrets

| Parameter | Description | Default |
|-----------|-------------|---------|
| `externalSecrets.enabled` | Enable External Secrets integration | `true` |
| `externalSecrets.refreshInterval` | Secret refresh interval | `1h` |
| `externalSecrets.secretStore.name` | Secret store name | `vault-cluster-backend` |
| `externalSecrets.secretStore.kind` | Secret store kind | `ClusterSecretStore` |

### Kubernetes Resources

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `resources.limits.cpu` | CPU limit | Not set |
| `resources.limits.memory` | Memory limit | Not set |
| `resources.requests.cpu` | CPU request | Not set |
| `resources.requests.memory` | Memory request | Not set |

## Usage Examples

### Multi-Vestaboard Deployment

Deploy multiple instances to control different Vestaboards:

**Office Board:**
```bash
helm install vestaboard-office ./deploy/chart \
  --set mqtt.broker.host=mqtt.office.local \
  --set mqtt.topicPrefix=office-board \
  --set mqtt.connection.clientId=vestaboard-office \
  --set application.httpPort=8001 \
  --set service.port=8001
```

**Lobby Board:**
```bash
helm install vestaboard-lobby ./deploy/chart \
  --set mqtt.broker.host=mqtt.office.local \
  --set mqtt.topicPrefix=lobby-board \
  --set mqtt.connection.clientId=vestaboard-lobby \
  --set application.httpPort=8002 \
  --set service.port=8002
```

Then control each board independently:
```bash
# Update office board
mosquitto_pub -t "office-board/message" -m "Meeting at 3pm"

# Update lobby board
mosquitto_pub -t "lobby-board/message" -m "Welcome!"
```

### Secure MQTT with TLS

Create a secret with TLS certificates:
```bash
kubectl create secret generic mqtt-tls-certs \
  --from-file=ca.crt=/path/to/ca.crt \
  --from-file=client.crt=/path/to/client.crt \
  --from-file=client.key=/path/to/client.key
```

Install with TLS enabled:
```bash
helm install vestaboard-mqtt ./deploy/chart -f - <<EOF
mqtt:
  broker:
    host: "secure-mqtt.example.com"
    port: "8883"
  connection:
    qos: "1"
  tls:
    enabled: true
    caCerts: "/etc/ssl/certs/ca.crt"
    certFile: "/etc/ssl/certs/client.crt"
    keyFile: "/etc/ssl/private/client.key"
  lwt:
    enabled: true
    topic: "vestaboard/status"
    qos: "1"

volumes:
  - name: mqtt-tls
    secret:
      secretName: mqtt-tls-certs

volumeMounts:
  - name: mqtt-tls
    mountPath: /etc/ssl/certs
    readOnly: true
  - name: mqtt-tls
    mountPath: /etc/ssl/private
    readOnly: true
EOF
```

### Vestaboard Note with Local API

```bash
helm install vestaboard-note ./deploy/chart -f - <<EOF
vestaboard:
  useLocalApi: true
  boardType: "note"
  localApi:
    host: "192.168.1.100"
    port: "7000"

mqtt:
  broker:
    host: "mqtt.local"
  topicPrefix: "vestaboard-note"
EOF
```

### Production Setup with Monitoring

```bash
helm install vestaboard-mqtt ./deploy/chart -f - <<EOF
replicaCount: 2

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/path: "/metrics"
  prometheus.io/port: "8000"

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 128Mi

mqtt:
  broker:
    host: "mqtt.production.example.com"
    port: "8883"
  connection:
    qos: "1"
  tls:
    enabled: true
    caCerts: "/etc/ssl/certs/mqtt-ca.crt"
  lwt:
    enabled: true
    topic: "vestaboard/status"
    qos: "1"

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 80
EOF
```

## Upgrading

```bash
# Upgrade with new values
helm upgrade vestaboard-mqtt ./deploy/chart -f my-values.yaml

# Upgrade with inline changes
helm upgrade vestaboard-mqtt ./deploy/chart \
  --set mqtt.broker.host=new-mqtt.example.com
```

## Uninstalling

```bash
helm uninstall vestaboard-mqtt
```

## Troubleshooting

### Check Pod Logs
```bash
kubectl logs -l app.kubernetes.io/name=vestaboard-mqtt -f
```

### Check Configuration
```bash
# View current values
helm get values vestaboard-mqtt

# View all computed values
helm get values vestaboard-mqtt --all
```

### Test MQTT Connection
```bash
# Port-forward to pod
kubectl port-forward svc/vestaboard-mqtt 8000:8000

# Check health
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics
```

### Common Issues

#### TLS Certificate Errors
- Ensure certificates are mounted correctly as volumes
- Check certificate paths match `mqtt.tls.*` settings
- Verify CA certificate includes full chain

#### MQTT Connection Failures
- Verify broker hostname is resolvable from pod
- Check network policies allow MQTT traffic
- Ensure MQTT credentials are correct in secrets

#### Multiple Vestaboards Not Working
- Verify each instance has a unique `mqtt.topicPrefix`
- Ensure each instance has unique `mqtt.connection.clientId`
- Check that service ports don't conflict

## Additional Resources

- [Main Project README](../../README.md)
- [Configuration Examples](values-examples.yaml)
- [MQTT Topics Documentation](../../CLAUDE.md#mqtt-topics)
- [Vestaboard API Documentation](https://docs.vestaboard.com/)

## Support

For issues and questions:
- GitHub Issues: [Link to your repo]
- Documentation: [Link to docs]
