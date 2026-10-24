"""Run as a stdio MCP server. Never print logs to stdout."""
from mcp.server.fastmcp import FastMCP
from campus import search_services, get_service_hours, find_study_spaces
from weather import get_weather_forecast

mcp = FastMCP("campus-info")
mcp.tool()(search_services)
mcp.tool()(get_service_hours)
mcp.tool()(find_study_spaces)
mcp.tool()(get_weather_forecast)

if __name__ == "__main__":
    mcp.run(transport="stdio")
