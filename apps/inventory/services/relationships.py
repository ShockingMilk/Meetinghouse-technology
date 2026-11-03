"""Shared validation, traversal, and replacement impact logic."""

from collections import defaultdict, deque

from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.inventory.models import AssetConnection, AssetDependency, AssetSpecification, CompatibilityVerification


def validate_connection(source_id: int | None, destination_id: int | None) -> None:
    """Validate a directed equipment link before saving it."""
    if source_id and source_id == destination_id:
        raise ValidationError({'destination': 'An asset cannot connect to itself.'})


def validate_compatibility_verification(verification: CompatibilityVerification) -> None:
    """Ensure the evidence is attached to the asset/connection it evaluates."""
    if verification.related_asset_id == verification.asset_id:
        raise ValidationError({'related_asset': 'Choose a different related asset.'})
    if verification.connection_id and verification.asset_id and verification.connection and verification.asset_id not in (verification.connection.source_id, verification.connection.destination_id):
        raise ValidationError({'connection': 'The selected connection must involve the reviewed asset.'})


def verification_state(record: CompatibilityVerification) -> dict:
    """Present recorded evidence with an explicit unknown fallback."""
    return {
        'outcome': record.outcome,
        'label': record.get_outcome_display(),
        'is_verified': record.outcome in ('verified', 'limited') and bool(record.verified_on and record.evidence_reference),
        'needs_follow_up': record.outcome == 'unknown' or not record.evidence_reference,
    }


def dependency_path(start_id: int, target_id: int, *, exclude_pk: int | None = None) -> list[int] | None:
    """Return an existing dependency path, using a bounded visited-set traversal."""
    graph = defaultdict(list)
    edges = AssetDependency.objects.exclude(required_asset__isnull=True, required_software__isnull=True)
    if exclude_pk:
        edges = edges.exclude(pk=exclude_pk)
    for source_id, asset_target, software_host in edges.values_list('dependent_asset_id', 'required_asset_id', 'required_software__host_asset_id'):
        target = asset_target or software_host
        if target and target != source_id:
            graph[source_id].append(target)
    queue = deque([(start_id, [start_id])])
    visited = set()
    while queue:
        node, path = queue.popleft()
        if node == target_id:
            return path
        if node in visited:
            continue
        visited.add(node)
        queue.extend((next_id, [*path, next_id]) for next_id in graph[node] if next_id not in visited)
    return None


def validate_dependency(dependent_id: int, required_id: int | None, *, exclude_pk: int | None = None) -> None:
    """Reject self-dependencies and any edge that would create a cycle."""
    if required_id is None:
        return
    if dependent_id == required_id:
        raise ValidationError({'required_asset': 'An asset cannot depend on itself.'})
    path = dependency_path(required_id, dependent_id, exclude_pk=exclude_pk)
    if path:
        raise ValidationError({'required_asset': 'This dependency would create a circular path: ' + ' → '.join(map(str, path))})


def existing_dependency_cycles() -> list[list[int]]:
    """Report legacy cycles without changing or deleting the recorded relationships."""
    graph = defaultdict(list)
    for source_id, asset_target, software_host in AssetDependency.objects.exclude(required_asset__isnull=True, required_software__isnull=True).values_list('dependent_asset_id', 'required_asset_id', 'required_software__host_asset_id'):
        target_id = asset_target or software_host
        if target_id and target_id != source_id:
            graph[source_id].append(target_id)
    cycles, reported, color = [], set(), {}
    for root in list(graph):
        if color.get(root, 0):
            continue
        path = [root]
        active_index = {root: 0}
        color[root] = 1
        stack = [(root, iter(graph[root]))]
        while stack:
            node, neighbors = stack[-1]
            try:
                neighbor = next(neighbors)
            except StopIteration:
                stack.pop()
                color[node] = 2
                active_index.pop(node, None)
                path.pop()
                continue
            if color.get(neighbor, 0) == 1:
                cycle = path[active_index[neighbor]:] + [neighbor]
                key = frozenset(cycle[:-1])
                if key not in reported:
                    reported.add(key)
                    cycles.append(cycle)
            elif color.get(neighbor, 0) == 0:
                color[neighbor] = 1
                active_index[neighbor] = len(path)
                path.append(neighbor)
                stack.append((neighbor, iter(graph[neighbor])))
    return cycles


def relationship_impact(asset) -> dict:
    """Return direct connections and bounded, cycle-safe dependency impact."""
    incoming = list(AssetConnection.objects.filter(destination=asset).select_related('source', 'source__room'))
    outgoing = list(AssetConnection.objects.filter(source=asset).select_related('destination', 'destination__room'))
    requirements = list(AssetDependency.objects.filter(dependent_asset=asset).select_related('required_asset', 'required_asset__room', 'required_software', 'required_software__host_asset'))
    dependents = list(AssetDependency.objects.filter(Q(required_asset=asset) | Q(required_software__host_asset=asset)).exclude(dependent_asset=asset).select_related('dependent_asset', 'dependent_asset__room', 'required_software'))

    # A queue and visited set bound traversal even if older data contains a cycle.
    graph = defaultdict(list)
    dependencies = AssetDependency.objects.exclude(required_asset__isnull=True, required_software__isnull=True).select_related('dependent_asset', 'required_asset', 'required_software', 'required_software__host_asset')
    for edge in dependencies:
        target_id = edge.required_asset_id or edge.required_software.host_asset_id
        if target_id != edge.dependent_asset_id:
            graph[target_id].append(edge)
    affected = []
    visited = {asset.pk}
    queue = deque([asset.pk])
    while queue:
        current = queue.popleft()
        for edge in graph[current]:
            if edge.dependent_asset_id not in visited:
                visited.add(edge.dependent_asset_id)
                affected.append(edge)
                queue.append(edge.dependent_asset_id)

    unknown_required = [edge for edge in requirements if edge.is_required and edge.verification_status != 'verified']
    specifications = list(AssetSpecification.objects.filter(asset=asset))
    unverified_specifications = [item for item in specifications if item.verification_status != 'verified']
    return {
        'incoming_connections': incoming,
        'outgoing_connections': outgoing,
        'requirements': requirements,
        'dependents': dependents,
        'transitive_impact': affected,
        'unknown_required': unknown_required,
        'specifications': specifications,
        'unverified_specifications': unverified_specifications,
    }


def replacement_impact(asset) -> dict:
    """Summarize what a replacement must be checked against without approving it."""
    impact = relationship_impact(asset)
    related = {edge.source_id: edge.source for edge in impact['incoming_connections']}
    related.update({edge.destination_id: edge.destination for edge in impact['outgoing_connections']})
    unverified_connections = [edge for edge in impact['incoming_connections'] + impact['outgoing_connections'] if edge.compatibility not in ('verified',)]
    required_interfaces = sorted({edge.interface for edge in impact['incoming_connections'] + impact['outgoing_connections'] if edge.interface})
    verification_history = list(CompatibilityVerification.objects.filter(
        Q(asset=asset) | Q(related_asset=asset),
    ).select_related('asset', 'related_asset', 'connection'))
    return {
        **impact,
        'connected_assets': sorted(related.values(), key=lambda item: item.inventory_number),
        'unverified_connections': unverified_connections,
        'required_interfaces': required_interfaces,
        'verification_history': verification_history,
        'needs_verification': bool(unverified_connections or impact['unknown_required'] or impact['unverified_specifications']),
    }
