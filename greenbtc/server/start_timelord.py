from __future__ import annotations

import logging
import pathlib
import sys
from typing import Dict, Optional

from greenbtc.consensus.constants import ConsensusConstants
from greenbtc.consensus.default_constants import DEFAULT_CONSTANTS
from greenbtc.rpc.timelord_rpc_api import TimelordRpcApi
from greenbtc.server.outbound_message import NodeType
from greenbtc.server.start_service import RpcInfo, Service, async_run
from greenbtc.timelord.timelord import Timelord
from greenbtc.timelord.timelord_api import TimelordAPI
from greenbtc.types.peer_info import PeerInfo
from greenbtc.util.greenbtc_logging import initialize_service_logging
from greenbtc.util.config import load_config, load_config_cli
from greenbtc.util.default_root import DEFAULT_ROOT_PATH

# See: https://bugs.python.org/issue29288
"".encode("idna")

SERVICE_NAME = "timelord"


log = logging.getLogger(__name__)


def create_timelord_service(
    root_path: pathlib.Path,
    config: Dict,
    constants: ConsensusConstants,
    connect_to_daemon: bool = True,
) -> Service[Timelord]:
    service_config = config[SERVICE_NAME]

    connect_peers = [PeerInfo(service_config["full_node_peer"]["host"], service_config["full_node_peer"]["port"])]
    overrides = service_config["network_overrides"]["constants"][service_config["selected_network"]]
    updated_constants = constants.replace_str_to_bytes(**overrides)

    node = Timelord(root_path, service_config, updated_constants)
    peer_api = TimelordAPI(node)
    network_id = service_config["selected_network"]

    rpc_info: Optional[RpcInfo] = None
    if service_config.get("start_rpc_server", True):
        rpc_info = (TimelordRpcApi, service_config.get("rpc_port", 8557))

    return Service(
        root_path=root_path,
        config=config,
        peer_api=peer_api,
        node=node,
        node_type=NodeType.TIMELORD,
        advertised_port=service_config["port"],
        service_name=SERVICE_NAME,
        server_listen_ports=[service_config["port"]],
        connect_peers=connect_peers,
        network_id=network_id,
        rpc_info=rpc_info,
        connect_to_daemon=connect_to_daemon,
    )


async def async_main() -> int:
    # TODO: refactor to avoid the double load
    config = load_config(DEFAULT_ROOT_PATH, "config.yaml")
    service_config = load_config_cli(DEFAULT_ROOT_PATH, "config.yaml", SERVICE_NAME)
    config[SERVICE_NAME] = service_config
    initialize_service_logging(service_name=SERVICE_NAME, config=config)
    service = create_timelord_service(DEFAULT_ROOT_PATH, config, DEFAULT_CONSTANTS)
    await service.setup_process_global_state()
    await service.run()

    return 0


def main() -> int:
    return async_run(async_main())


if __name__ == "__main__":
    sys.exit(main())
