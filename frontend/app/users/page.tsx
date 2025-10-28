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
        requireQuery
        minQueryLength={1}
        disablePagination
      />
    </div>
  );
}
