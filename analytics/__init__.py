"""Analytics module for executing verified SQL analytical queries and reporting metrics."""

from analytics.query_runner import QueryResult, QueryRunner, query_runner

__all__ = ["QueryRunner", "QueryResult", "query_runner"]
