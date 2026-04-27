from .weather_mapping import WEATHER_MAPPING, DATE_MAPPING, DAYS_MAPPING

GRAPH_SAVED_DIR="/home/ubuntu/lun_dev/WorkFlowAgent_Rebuild/graph_img"

# Fast API Url
FAST_BASE_PORT="8088"
FAST_BASE_PATH=f"http://localhost:{FAST_BASE_PORT}"

# Upload File
FAST_UPLOAD_PARH=f"{FAST_BASE_PATH}/upload_tools"
FAST_GETTOOLS_PARH=f"{FAST_BASE_PATH}/get_files_in_folder"
FAST_REMOVEDTOOLS_PARH=f"{FAST_BASE_PATH}/remove_tools"

# Tools service API (agent_tool)
# agent_tool 預設在本機以 1235 提供 /weather/ 與 /flightinformation/
TOOLS_BASE_PORT="1235"
TOOLS_BASE_URL=f"http://localhost:{TOOLS_BASE_PORT}"
WEATHER_SEARCH_TOOLS=f"{TOOLS_BASE_URL}/weather/"
TRAINSPORT_SEARCH_TOOLS=f"{TOOLS_BASE_URL}/flightinformation/"


# Weather loacation name translate mapping
WEATHER_LOCATION_MAPPING=WEATHER_MAPPING
WEATHER_DATE_MAPPING=DATE_MAPPING
WEATHER_DAYS_MAPPING=DAYS_MAPPING