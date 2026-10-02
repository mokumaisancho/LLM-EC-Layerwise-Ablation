from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Callable, Iterable

WILDCARD = "*"
SCOPE_FIELDS = ("task", "model", "tool", "context", "perspective")
SourceValidator = Callable[[str], bool]


@dataclass(frozen=True)
class Scope:
    task: str = WILDCARD
    model: str = WILDCARD
    tool: str = WILDCARD
    context: str = WILDCARD
    perspective: str = WILDCARD

    def matches(self, query: "Scope") -> bool:
        for name in SCOPE_FIELDS:
            item = getattr(self, name)
            q = getattr(query, name)
            if item != WILDCARD and q != WILDCARD and item != q:
                return False
        return True

    def specificity_for(self, query: "Scope") -> int:
        return sum(
            1
            for name in SCOPE_FIELDS
            if getattr(self, name) != WILDCARD and getattr(self, name) == getattr(query, name)
        )


@dataclass(frozen=True)
class CacheItem:
    item_id: str
    kind: str
    claim_key: str
    payload: object
    payload_digest: str
    scope: Scope
    source_refs: tuple[str, ...]
    verified: bool
    authority: str
    created_seq: int
    expires_seq: int | None
    status: str


@dataclass(frozen=True)
class RetrievalDecision:
    status: str
    selected: tuple[CacheItem, ...]
    reasons: tuple[str, ...]
    requires_revalidation: bool = True
    examined_candidates: int = 0


class EpistemicCache:
    """Disposable memory/learning cache over an external authoritative source ledger.

    Cache entries are never authority. A root source validator is required for an
    entry to become eligible. Missing/invalid provenance, unresolved conflict,
    expiry, revocation, or ambiguity causes source fallback rather than guessing.
    """

    def __init__(self, source_validator: SourceValidator | None = None) -> None:
        self._source_validator: SourceValidator = source_validator or (lambda _ref: False)
        self._items: dict[str, CacheItem] = {}
        self._relations: set[tuple[str, str, str]] = set()
        self._seq = 0
        self._scope_index: dict[str, dict[str, set[str]]] = {
            name: {} for name in SCOPE_FIELDS
        }
        self._kind_index: dict[str, set[str]] = {}
        self._claim_index: dict[str, set[str]] = {}

    @staticmethod
    def _digest(payload: object) -> str:
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _index_item(self, item: CacheItem) -> None:
        for name in SCOPE_FIELDS:
            value = getattr(item.scope, name)
            self._scope_index[name].setdefault(value, set()).add(item.item_id)
        self._kind_index.setdefault(item.kind, set()).add(item.item_id)
        self._claim_index.setdefault(item.claim_key, set()).add(item.item_id)

    def _external_source_valid(self, ref: str) -> bool:
        try:
            return bool(self._source_validator(ref))
        except Exception:
            return False

    def add_memory(
        self,
        item_id: str,
        payload: object,
        *,
        claim_key: str,
        scope: Scope,
        verified: bool,
        authority: str,
        source_refs: Iterable[str] = (),
        ttl: int | None = None,
    ) -> CacheItem:
        if item_id in self._items:
            raise ValueError("DUPLICATE_ITEM")
        if not claim_key:
            raise ValueError("CLAIM_KEY_REQUIRED")
        seq = self._next_seq()
        refs = tuple(source_refs)
        source_ok = bool(refs) and all(self._external_source_valid(ref) for ref in refs)
        status = (
            "ACTIVE"
            if verified and authority == "independent" and source_ok
            else "QUARANTINED"
        )
        item = CacheItem(
            item_id,
            "MEMORY",
            claim_key,
            payload,
            self._digest(payload),
            scope,
            refs,
            verified,
            authority,
            seq,
            None if ttl is None else seq + ttl,
            status,
        )
        self._items[item_id] = item
        self._index_item(item)
        return item

    def add_learning(
        self,
        item_id: str,
        payload: object,
        *,
        claim_key: str,
        scope: Scope,
        source_refs: Iterable[str],
        ttl: int | None = None,
    ) -> CacheItem:
        if item_id in self._items:
            raise ValueError("DUPLICATE_ITEM")
        if not claim_key:
            raise ValueError("CLAIM_KEY_REQUIRED")
        refs = tuple(source_refs)
        if not refs:
            raise ValueError("SOURCE_REQUIRED")
        if not all(self._ref_valid(ref, self._seq, set()) for ref in refs):
            raise ValueError("UNVERIFIED_SOURCE")
        seq = self._next_seq()
        item = CacheItem(
            item_id,
            "LEARNING",
            claim_key,
            payload,
            self._digest(payload),
            scope,
            refs,
            True,
            "derived",
            seq,
            None if ttl is None else seq + ttl,
            "ACTIVE",
        )
        self._items[item_id] = item
        self._index_item(item)
        for ref in refs:
            if ref in self._items:
                self._relations.add((item_id, "derived_from", ref))
        return item

    def _is_expired(self, item: CacheItem, now: int) -> bool:
        return item.expires_seq is not None and now > item.expires_seq

    def _ref_valid(self, ref: str, now: int, seen: set[str]) -> bool:
        if ref not in self._items:
            return self._external_source_valid(ref)
        if ref in seen:
            return False
        seen = set(seen)
        seen.add(ref)
        item = self._items[ref]
        if item.status != "ACTIVE" or self._is_expired(item, now):
            return False
        if item.item_id in self._superseded():
            return False
        if item.kind == "MEMORY":
            return (
                item.verified
                and item.authority == "independent"
                and bool(item.source_refs)
                and all(self._external_source_valid(root) for root in item.source_refs)
            )
        if item.kind == "LEARNING":
            return bool(item.source_refs) and all(
                self._ref_valid(source, now, seen) for source in item.source_refs
            )
        return False

    def relate(self, left: str, relation: str, right: str) -> None:
        if left not in self._items or right not in self._items:
            raise KeyError("UNKNOWN_ITEM")
        if relation not in {
            "supports",
            "contradicts",
            "supersedes",
            "exception_to",
            "applies_to",
            "derived_from",
        }:
            raise ValueError("UNKNOWN_RELATION")
        self._relations.add((left, relation, right))

    def revoke(self, item_id: str) -> None:
        item = self._items[item_id]
        self._items[item_id] = CacheItem(**{**item.__dict__, "status": "REVOKED"})

    def _superseded(self) -> set[str]:
        return {
            right
            for left, rel, right in self._relations
            if rel == "supersedes"
            and self._items.get(left)
            and self._items[left].status == "ACTIVE"
        }

    def _relation_resolves(self, left: str, right: str) -> bool:
        return any(
            (a == left and b == right) or (a == right and b == left)
            for a, rel, b in self._relations
            if rel in {"supersedes", "exception_to"}
        )

    def _conflicts(self, candidates: list[CacheItem]) -> bool:
        ids = {item.item_id for item in candidates}
        superseded = self._superseded()
        for left, rel, right in self._relations:
            if (
                rel == "contradicts"
                and left in ids
                and right in ids
                and left not in superseded
                and right not in superseded
                and not self._relation_resolves(left, right)
            ):
                return True

        by_claim: dict[str, list[CacheItem]] = {}
        for item in candidates:
            by_claim.setdefault(item.claim_key, []).append(item)
        for items in by_claim.values():
            active = [item for item in items if item.item_id not in superseded]
            digests = {item.payload_digest for item in active}
            if len(digests) <= 1:
                continue
            unresolved = False
            for i, left in enumerate(active):
                for right in active[i + 1 :]:
                    if left.payload_digest == right.payload_digest:
                        continue
                    if not self._relation_resolves(left.item_id, right.item_id):
                        unresolved = True
                        break
                if unresolved:
                    break
            if unresolved:
                return True
        return False

    def provenance(self, item_id: str) -> tuple[str, ...]:
        seen: list[str] = []

        def walk(current: str) -> None:
            if current in seen:
                return
            seen.append(current)
            item = self._items.get(current)
            if item:
                for ref in item.source_refs:
                    walk(ref)

        walk(item_id)
        return tuple(seen)

    def relations(self, item_id: str) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            sorted(
                relation
                for relation in self._relations
                if relation[0] == item_id or relation[2] == item_id
            )
        )

    def _candidate_ids(self, query: Scope, kind: str | None) -> set[str]:
        candidate: set[str] | None = None
        if kind is not None:
            candidate = set(self._kind_index.get(kind, set()))
        for name in SCOPE_FIELDS:
            q = getattr(query, name)
            if q == WILDCARD:
                continue
            allowed = set(self._scope_index[name].get(q, set()))
            allowed.update(self._scope_index[name].get(WILDCARD, set()))
            candidate = allowed if candidate is None else candidate & allowed
        return set(self._items) if candidate is None else candidate

    def retrieve(
        self,
        query: Scope,
        *,
        kind: str | None = None,
        limit: int = 5,
        now_seq: int | None = None,
    ) -> RetrievalDecision:
        now = self._seq if now_seq is None else now_seq
        superseded = self._superseded()
        pool = self._candidate_ids(query, kind)
        candidates: list[CacheItem] = []
        for item_id in pool:
            item = self._items[item_id]
            if item.status != "ACTIVE" or item.item_id in superseded:
                continue
            if kind and item.kind != kind:
                continue
            if self._is_expired(item, now):
                continue
            if not item.scope.matches(query):
                continue
            if not self._ref_valid(item.item_id, now, set()):
                continue
            candidates.append(item)

        if not candidates:
            return RetrievalDecision(
                "FALLBACK_SOURCE",
                (),
                ("NO_ELIGIBLE_CACHE_ENTRY",),
                True,
                len(pool),
            )

        if self._conflicts(candidates):
            return RetrievalDecision(
                "FALLBACK_SOURCE",
                (),
                ("UNRESOLVED_CONFLICT",),
                True,
                len(pool),
            )

        candidates.sort(
            key=lambda item: (
                -item.scope.specificity_for(query),
                0 if item.kind == "MEMORY" else 1,
                len(self.provenance(item.item_id)),
                -item.created_seq,
                item.item_id,
            )
        )

        selected: list[CacheItem] = []
        seen_claims: set[str] = set()
        for item in candidates:
            if item.claim_key in seen_claims:
                continue
            selected.append(item)
            seen_claims.add(item.claim_key)
            if len(selected) >= limit:
                break

        return RetrievalDecision(
            "USE_CACHE",
            tuple(selected),
            ("ELIGIBLE_NONCONFLICTING_CACHE",),
            True,
            len(pool),
        )
