"use server";

import Results, { type Option } from "@/components/ResultTable";
import { Suspense } from "react";
import TransactionStats from "@/components/Transactions/Stats";
import RefreshButton from "@/components/RefreshButton";

export interface TransactionStats {
  total_txns: number;
  total_blocked: number;
  total_review: number;
  total_clean: number;
}

const options: Option[] = [
  {
    name: "Transaction ID",
    item: "id",
    width: "250px",
    label: {
      size: "sm",
      text: "txn_id",
      icon: "credit-card",
    },
  },
  {
    name: "Sender",
    item: "sender",
    width: "100px",
    label: {
      size: "sm",
      text: "sender",
      className: "font-mono",
    },
  },
  {
    name: "Receiver",
    item: "receiver",
    width: "100px",
    label: {
      size: "sm",
      text: "receiver",
      className: "font-mono",
    },
  },
  {
    name: "Amount",
    item: "amount",
    width: "125px",
    type: "currency",
    sortable: true,
    label: {
      text: "amount",
    },
  },
  {
    name: "Risk Score",
    item: "fraud_score",
    width: "125px",
    type: "risk",
    sortable: true,
    label: {
      badge: {
        text: "fraud_score",
      },
    },
  },
  {
    name: "Date",
    item: "timestamp",
    type: "datetime",
    width: "225px",
    label: {
      size: "sm",
      text: "timestamp",
      icon: "calendar",
    },
    sortable: true,
    defaultSort: true,
    defaultOrder: "desc",
  },
  {
    name: "Location",
    item: "location",
    width: "225px",
    label: {
      size: "sm",
      text: "location",
      icon: "map-pin",
    },
  },
  {
    name: "Status",
    item: "fraud_status",
    width: "125px",
    type: "fraud",
    label: {
      badge: {
        text: "fraud_status",
      },
    },
  },
];

const API_BASE_URL = process.env.BASE_URL || "http://localhost:8080/api";

export default async function TransactionsPage() {
  async function handleSearch(
    _page: number = 1,
    _size: number = 10,
    _orderBy: string = "date",
    _order: "asc" | "desc" = "desc",
    query?: string
  ) {
    "use server";
    const q = (query ?? "").trim();
    if (!q) return { results: [], total_pages: 0, total: 0 } as any;
    try {
      // Normalize to exactly-once encoding to avoid %252B double-encoding
      let rawId = q;
      try {
        // If q was already encoded, decode once
        rawId = decodeURIComponent(q);
      } catch {}
      const encodedId = encodeURIComponent(rawId);
      const detailRes = await fetch(
        `${API_BASE_URL}/transaction/${encodedId}`,
        { cache: "no-store" }
      );
      if (detailRes.ok) {
        const detail = await detailRes.json();
        console.log(detail);
        const row = {
          id: rawId,
          txn_id: detail?.txn?.txn_id ?? rawId,
          amount: detail?.txn?.amount ?? 0,
          timestamp: detail?.txn?.timestamp ?? "",
          location: detail?.txn?.location ?? "",
          fraud_score: detail?.txn?.fraud_score ?? 0,
          fraud_status: detail?.txn?.fraud_status ?? "",
          sender: detail?.src?.account?.id,
          receiver: detail?.dest?.account?.id,
        } as any;
        return { results: [row], total_pages: 1, total: 1 } as any;
      }
      // If non-OK, return empty (no fallback endpoint)
      return { results: [], total_pages: 0, total: 0 } as any;
    } catch {
      return { results: [], total_pages: 0, total: 0 } as any;
    }
  }

  return (
    <div className="space-y-6 flex flex-col grow">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Transaction Explorer</h1>

        <div className="mb-2 flex items-center justify-between gap-3">
          <p className="text-muted-foreground">
            Search and explore transaction details and patterns
          </p>
          <RefreshButton />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Suspense fallback={<TransactionStats loading />}>
          <TransactionStats />
        </Suspense>
      </div>
      <Results
        handleSearch={handleSearch}
        title="Transactions"
        options={options}
        requireQuery
        minQueryLength={1}
        disablePagination
      />
    </div>
  );
}
