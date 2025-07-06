import json
import logging
from collections.abc import Sequence
from typing import Any, Union

from google.cloud import logging as google_cloud_logging
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult


class CloudTraceLoggingSpanExporter(CloudTraceSpanExporter):
    """
    An extended version of CloudTraceSpanExporter that logs span data to Google Cloud Logging.
    """

    def __init__(
        self,
        logging_client: Union[google_cloud_logging.Client, None] = None,
        debug: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the exporter with Google Cloud clients and configuration.

        :param logging_client: Google Cloud Logging client
        :param debug: Enable debug mode for additional logging
        :param kwargs: Additional arguments to pass to the parent class
        """
        super().__init__(**kwargs)
        self.debug = debug
        self.logging_client = logging_client or google_cloud_logging.Client(
            project=self.project_id
        )
        self.logger = self.logging_client.logger(__name__)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """
        Export the spans to Google Cloud Logging and Cloud Trace.

        :param spans: A sequence of spans to export
        :return: The result of the export operation
        """
        for span in spans:
            span_context = span.get_span_context()
            trace_id = format(span_context.trace_id, "x")
            span_id = format(span_context.span_id, "x")
            span_dict = json.loads(span.to_json())

            span_dict["trace"] = f"projects/{self.project_id}/traces/{trace_id}"
            span_dict["span_id"] = span_id

            if self.debug:
                print(span_dict)

            # Log the span data to Google Cloud Logging
            self.logger.log_struct(
                span_dict,
                labels={
                    "type": "agent_telemetry",
                    "service_name": "gemini-adk-demo",
                },
                severity="INFO",
            )
        # Export spans to Google Cloud Trace using the parent class method
        return super().export(spans)
