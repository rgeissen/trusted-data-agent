import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

async def list_chart_mcp_tools(server_http_url: str):
    """
    Connects to the specified chart MCP server using SSE transport
    and prints all available tools.

    Args:
        server_http_url (str): The HTTP URL of the chart MCP server
                                (e.g., "http://localhost:1122/mcp").
    """
    print(f"Attempting to connect to Chart MCP server at: {server_http_url} using SSE transport.")

    # Define the server configuration for MultiServerMCPClient
    server_configs = {
        'chart_mcp_server': {
            "url": server_http_url, # Use 'url' for HTTP/SSE transport
            "transport": "sse"      # Changed transport to "sse"
        }
    }

    try:
        # Initialize the MultiServerMCPClient with the chart server configuration
        mcp_client = MultiServerMCPClient(server_configs)

        # Create a session with the chart server
        # The session context manager ensures proper connection and disconnection
        async with mcp_client.session("chart_mcp_server") as temp_session:
            print("Successfully connected to the Chart MCP server.")

            # Load tools from the chart server using load_mcp_tools
            loaded_tools = await load_mcp_tools(temp_session)

            if loaded_tools:
                print("\n--- Available Tools on Chart MCP Server ---")
                for tool in loaded_tools:
                    print(f"- Name: {tool.name}")
                    print(f"  Description: {tool.description}")
                    print(f"  Arguments: {tool.args}\n") # tool.args provides the arguments schema
            else:
                print("No tools found on the Chart MCP server.")

    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure the chart MCP server is running and accessible at the specified HTTP URL.")

if __name__ == "__main__":
    # The HTTP URL of your chart MCP server for SSE transport
    CHART_MCP_SERVER_HTTP_URL = "http://localhost:1122/sse"
    
    # Run the asynchronous function
    asyncio.run(list_chart_mcp_tools(CHART_MCP_SERVER_HTTP_URL))
