"""
██████╗ ██╗  ██╗ █████╗ ███╗   ██╗████████╗ ██████╗ ███╗   ███╗
██╔══██╗██║  ██║██╔══██╗████╗  ██║╚══██╔══╝██╔═══██╗████╗ ████║
██████╔╝███████║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
██╔═══╝ ██╔══██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
██║     ██║  ██║██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝

Core Module Models Package

Copyright (c) 2025 Rıza Emre ARAS <r.emrearas@proton.me>
Licensed under AGPL-3.0 - see LICENSE file for details
Third-party licenses - see THIRD_PARTY_LICENSES file for details
WireGuard® is a registered trademark of Jason A. Donenfeld.
"""

from .client_models import (
    WireGuardClient,
    ClientAddResult,
    ClientRemoveResult,
    ClientListResult,
    ClientExportResult,
    LatestClientsResult,
    ClientInfo,
    PaginationInfo
)

from .service_models import (
    ServiceStatus,
    ClientStatistics,
    ServerConfig,
    SystemInfo,
    ServiceHealth,
    ServiceLogs,
    RestartResult,
    FirewallConfiguration,
    InterfaceStatistics
)

from .network_models import (
    TransferStats,
    PeerInfo,
    NetworkInfo,
    SubnetChangeValidation,
    NetworkAnalysis,
    NetworkValidationResult,
    NetworkMigrationResult,
    MainInterfaceInfo
)

from .config_models import (
    TweakSettingsResponse,
    TweakModificationResult
)

from .storage_models import (
    ClientDatastoreInfo,
    ActiveConnectionsMap
)

from .util_models import (
    SuccessResponse,
    ErrorResponse,
    TransferData,
    WireGuardShowData
)

from phantom.models.base import BaseModel

__all__ = [
    'WireGuardClient', 'ClientAddResult', 'ClientRemoveResult',
    'ClientListResult', 'ClientExportResult', 'LatestClientsResult',
    'ClientInfo', 'PaginationInfo',
    'ServiceStatus', 'ClientStatistics', 'ServerConfig', 'SystemInfo',
    'ServiceHealth', 'ServiceLogs', 'RestartResult',
    'FirewallConfiguration', 'InterfaceStatistics',
    'TransferStats', 'PeerInfo', 'NetworkInfo',
    'SubnetChangeValidation',
    'NetworkAnalysis', 'NetworkValidationResult',
    'NetworkMigrationResult', 'MainInterfaceInfo',
    'TweakSettingsResponse', 'TweakModificationResult',
    'ClientDatastoreInfo', 'ActiveConnectionsMap',
    'SuccessResponse', 'ErrorResponse', 'TransferData', 'WireGuardShowData',
    'BaseModel'
]
