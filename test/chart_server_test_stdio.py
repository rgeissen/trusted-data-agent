import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

async def list_chart_mcp_tools(server_command_path: str):
    """
    Connects to the specified chart MCP server and prints all available tools.

    Args:
        server_command_path (str): The path to the chart MCP server executable.
    """
    # The arguments for the stdio transport
    command_args = ["--transport", "stdio"]
    print(f"Attempting to connect to Chart MCP server using command: {server_command_path} with args: {command_args}")

    # Define the server configuration for MultiServerMCPClient
    server_configs = {
        'chart_mcp_server': {
            "command": server_command_path, # Only the executable path here
            "args": command_args,          # Arguments moved to a separate 'args' key
            "transport": "stdio"           # Using stdio transport
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
        print("Please ensure the chart MCP server executable is correct and accessible.")
        print("Also, confirm that the executable supports the '--transport stdio' argument.")

if __name__ == "__main__":
    # The path to your chart MCP server executable for stdio transport
    CHART_MCP_SERVER_EXECUTABLE = "/opt/homebrew/bin/mcp-server-chart"
    
    # Run the asynchronous function
    asyncio.run(list_chart_mcp_tools(CHART_MCP_SERVER_EXECUTABLE))
