"use server";

import Results, { type Option } from "@/components/ResultTable";
import UserStats from "@/components/Users/Stats";
import { Suspense } from "react";
import RefreshButton from "@/components/RefreshButton";

const options: Option[] = [
  {
    name: "Name",
    item: "name",
    width: "275px",
    sortable: true,
    defaultSort: true,
    label: {
      size: "md",
      text: "name",
      icon: "user",
    },
  },
  {
    name: "ID",
    item: "id",
    width: "75px",
    label: {
      subtitle: "id",
    },
  },
  {
    name: "Email",
    item: "email",
    width: "300px",
    label: {
      size: "sm",
      text: "email",
      icon: "mail",
      className: "lowercase",
    },
  },
  {
    name: "Location",
    item: "location",
    width: "175px",
    label: {
      size: "sm",
      text: "location",
      icon: "map-pin",
    },
  },
  {
    name: "Age",
    item: "age",
    width: "100px",
    label: {
      size: "sm",
      text: "age",
    },
  },
  {
    name: "Risk Score",
    item: "risk_score",
    width: "150px",
    type: "risk",
    sortable: true,
    label: {
      badge: {
        text: "risk_score",
      },
    },
  },
  {
    name: "Signup Date",
    item: "signup_date",
    type: "date",
    width: "200px",
    sortable: true,
    label: {
      size: "sm",
      text: "signup_date",
      icon: "calendar",
    },
  },
];

const API_BASE_URL = process.env.BASE_URL || "http://localhost:8080/api";

export default async function UsersPage() {
  const countRes = await fetch(`${API_BASE_URL}/users/count`, {
    cache: "no-store",
  });
  const { count: totalUsers = 0 } = countRes.ok
    ? await countRes.json()
    : { count: 0 };
  async function handleSearch(
    _page: number = 1,
    _size: number = 10,
    _orderBy: string = "date",
    _order: "asc" | "desc" = "desc",
    query?: string
  ) {
    "use server";
    const q = (query ?? "").trim();
    if (!q) {
      try {
        const countRes = await fetch(`${API_BASE_URL}/users/count`, {
          cache: "no-store",
        });
        const { count = 0 } = countRes.ok
          ? await countRes.json()
          : { count: 0 };
        const limit = Math.min(100, Math.max(1, Number(count || 0)));
        const ids: string[] = [];
        for (let i = 0; i < limit; i++) {
          const n =
            1 + Math.floor(Math.random() * Math.max(1, Number(count || 1)));
          ids.push(`U${n.toString().padStart(7, "0")}`);
        }
        const res = await fetch(`${API_BASE_URL}/users/summary`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ids }),
          cache: "no-store",
        });
        const rows = res.ok ? await res.json() : [];
        const start = (_page - 1) * _size;
        const end = start + _size;
        const pageRows = rows.slice(start, end);
        const total_pages = Math.max(1, Math.ceil(rows.length / _size));
        return { results: pageRows, total_pages, total: rows.length } as any;
      } catch {
        return { results: [], total_pages: 0, total: 0 } as any;
      }
    }
    try {
      const res = await fetch(
        `${API_BASE_URL}/users/${encodeURIComponent(q)}`,
        { cache: "no-store" }
      );
      if (res.ok) {
        const data = await res.json();
        const u = (data?.user ?? {}) as any;
        const row = {
          id: u.id ?? q,
          name: u.name ?? "",
          email: u.email ?? "",
          location: u.location ?? "",
          age: u.age ?? 0,
          risk_score: u.risk_score ?? 0,
          signup_date: u.signup_date ?? "",
        } as any;
        return { results: [row], total_pages: 1, total: 1 } as any;
      }
    } catch {}
    return { results: [], total_pages: 0, total: 0 } as any;
  }

  return (
    <div className="space-y-6 flex flex-col grow">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">User Explorer</h1>

        <div className="mb-2 flex items-center justify-between gap-3">
          <p className="text-muted-foreground">
            Browse and search user profiles with detailed information
          </p>
          <RefreshButton />
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        <Suspense fallback={<UserStats loading />}>
          <UserStats />
        </Suspense>
      </div>
      <Results
        handleSearch={handleSearch}
        title="Users"
        options={options}
        requireQuery={false}
        minQueryLength={1}
        disablePagination={false}
        randomType="user"
        randomLabel="Random User"
        randomMax={Number(totalUsers || 0)}
      />
    </div>
  );
}
