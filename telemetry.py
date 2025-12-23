import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

def setup_telemetry(service_name: str = "inventory-registry"):
    """
    Sets up OpenTelemetry tracing.
    
    Defaults to Console exporter if OTEL_EXPORTER_OTLP_ENDPOINT is not set.
    """
    
    # Create a Resource to identify the service
    resource = Resource.create(attributes={
        "service.name": service_name,
    })

    provider = TracerProvider(resource=resource)
    
    # Check if we have an OTLP endpoint configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    if otlp_endpoint:
        # Configure OTLP Exporter (standard for most backends)
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        print(f"🔭 OTel: Configured OTLP exporter to {otlp_endpoint}")
    else:
        # Fallback to Console Exporter for local dev / no-setup
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
        print("🔭 OTel: Configured Console exporter (local mode)")

    # Set the global tracer provider
    trace.set_tracer_provider(provider)
    
    return trace.get_tracer(service_name)
