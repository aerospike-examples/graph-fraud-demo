"use client";

import { useEffect, useRef, useState } from "react";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Eye } from "lucide-react";
import Pagination from "./Pagination";
import clsx from "clsx";
import Search from "./Search";
import { type LabelProps } from "../Label";
import { Skeleton } from "../ui/skeleton";
import TableData from "./TableData";

export interface Option {
  name: string;
  item: string;
  widthClass?: string;
  sortable?: boolean;
  defaultSort?: boolean;
  defaultOrder?: "asc" | "desc";
  className?: string;
  type?: "date" | "datetime" | "currency" | "risk" | "fraud";
  label: LabelProps;
}

interface SearchResult {
  results: Record<string, any>[];
  total_pages: number;
  total: number;
}

interface Props {
  handleSearch: (
    page: number,
    size: number,
    orderBy: string,
    order: "asc" | "desc",
    query?: string
  ) => Promise<SearchResult>;
  title: string;
  options: Option[];
  requireQuery?: boolean;
  minQueryLength?: number;
  disablePagination?: boolean;
  randomType?: "user" | "transaction";
  randomLabel?: string;
  randomMax?: number;
}

const Results = ({
  handleSearch,
  title,
  options,
  requireQuery = false,
  minQueryLength = 1,
  disablePagination = false,
  randomType,
  randomLabel,
  randomMax,
}: Props) => {
  const pathname = usePathname();
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState<number>(0);
  const [totalEntries, setTotalEntries] = useState<number>(0);
  const [orderBy, setOrderBy] = useState<string>(
    options.filter((opt) => opt.defaultSort)[0]?.item ??
      options.find((opt) => opt.sortable)?.item ??
      ""
  );
  const [order, setOrder] = useState<"asc" | "desc">(
    options.filter((opt) => opt.defaultSort)[0]?.defaultOrder ?? "asc"
  );
  const [results, setResults] = useState<Record<string, any>[]>([]);
  const [loading, setLoading] = useState(true);
  const loaded = useRef(false);
  const lastQueryRef = useRef<string>("");
  const searchApiRef = useRef<{
    setQuery: (s: string) => void;
    submit: () => void;
  } | null>(null);

  const fetchData = async (
    page: number = currentPage,
    size: number = pageSize,
    oB: string = orderBy,
    o: "asc" | "desc" = order,
    q?: string
  ) => {
    setLoading(true);
    const query = (q ?? lastQueryRef.current ?? "").trim();
    if (requireQuery && query.length < minQueryLength) {
      setResults([]);
      setTotalPages(0);
      setTotalEntries(0);
      setTimeout(() => setLoading(false), 150);
      return;
    }
    lastQueryRef.current = query;
    const search = await handleSearch(page, size, oB, o, query);
    setResults(search.results);
    setTotalPages(search.total_pages);
    setTotalEntries(search.total);
    setTimeout(() => setLoading(false), 300);
  };

  useEffect(() => {
    if (!loaded.current) {
      if (requireQuery) {
        setLoading(false);
      } else {
        fetchData();
      }
      loaded.current = true;
    }
  }, [requireQuery]);

  const handleSort = (key: string) => {
    if (loading) return;
    let o: "asc" | "desc" = "asc";
    if (orderBy === key) o = order === "asc" ? "desc" : "asc";
    setOrderBy(key);
    setOrder(o);
    fetchData(currentPage, pageSize, key, o);
  };

  const handlePageSize = (size: number) => {
    if (loading) return;
    setPageSize(size);
    fetchData(currentPage, size);
  };

  const handlePagination = (page: number) => {
    if (loading) return;
    setCurrentPage(page);
    fetchData(page);
  };

  return (
    <Card className="grow flex flex-col">
      <CardHeader className="gap-4">
        <CardTitle>{title}</CardTitle>
        <div className="flex items-center gap-2 justify-between">
          <Search
            fetchData={(q) =>
              fetchData(currentPage, pageSize, orderBy, order, q)
            }
            placeholder={`Search ${title} by ID`}
            setCurrentPage={() => setCurrentPage(1)}
            minQueryLength={minQueryLength}
            register={(api) => {
              searchApiRef.current = api;
            }}
          />
          {randomType && searchApiRef.current ? (
            <div className="ml-2">
              <button
                type="button"
                className="text-xs px-2 py-1 border rounded"
                onClick={() => {
                  if (!searchApiRef.current) return;
                  const { setQuery, submit } = searchApiRef.current;
                  let id = "";
                  if (randomType === "transaction") {
                    if (results && results.length > 0) {
                      const idx = Math.floor(Math.random() * results.length);
                      console.log(results[0])
                      id = String(results[idx]?.id ?? "");
                    }
                  } else {
                    const max = Math.max(1, Number(randomMax || 9_999_999));
                    const rnd = Math.floor(Math.random() * max) + 1;
                    id = `U${rnd.toString().padStart(7, "0")}`;
                  }
                  if (id) {
                    setQuery("");
                    setQuery(id);
                    submit();
                  }
                }}
              >
                {randomLabel ??
                  (randomType === "user"
                    ? "Random User"
                    : "Random Transaction")}
              </button>
            </div>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="grow overflow-x-auto flex flex-col">
        <table className="w-full grow table-fixed">
          <thead>
            <tr className="border-b">
              {options.map(({ name, item, sortable, widthClass }) => (
                <th
                  key={item}
                  className={clsx(
                    "text-left p-3 font-medium",
                    sortable && "cursor-pointer hover:bg-muted/50",
                    widthClass
                  )}
                  {...(sortable ? { onClick: () => handleSort(item) } : {})}
                >
                  {name +
                    (sortable
                      ? orderBy !== item
                        ? ""
                        : order === "asc"
                        ? " ↑"
                        : " ↓"
                      : "")}
                </th>
              ))}
              <th className="max-w-[150px] min-w-[150px] w-[150px]"></th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: pageSize }).map((_, idx) => (
                <tr key={idx} className="border-b hover:bg-muted/50">
                  {Array.from({ length: options.length }).map((_, idx) => (
                    <td className="p-3 h-[61px]" key={idx}>
                      <Skeleton className="h-[20px] w-[90%] rounded-full" />
                    </td>
                  ))}
                  <td className="p-3">
                    <Button variant="outline" size="sm">
                      <Eye className="h-4 w-4 mr-1" />
                      View Details
                    </Button>
                  </td>
                </tr>
              ))
            ) : results?.length > 0 ? (
              results.map((result: Record<string, any>) => (
                <tr
                  key={result.id}
                  className={clsx(
                    "border-b hover:bg-muted/50",
                    (result?.fraud_status === "review" ||
                      result?.fraud_status === "blocked") &&
                      "bg-red-50/30 dark:bg-red-950/10 border-l-2 border-l-red-200"
                  )}
                >
                  {options.map((opts, idx) => (
                    <TableData {...opts} key={idx} result={result} />
                  ))}
                  <td className="p-3">
                    <Link href={`${pathname}/${encodeURIComponent(result.id)}`}>
                      <Button variant="outline" size="sm">
                        <Eye className="h-4 w-4 mr-1" />
                        View Details
                      </Button>
                    </Link>
                  </td>
                </tr>
              ))
            ) : (
              <tr className="w-full h-full">
                <td
                  className="text-muted-foreground w-full h-full text-center"
                  colSpan={options.length + 1}
                  rowSpan={pageSize}
                >
                  No {title} found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </CardContent>
      {!disablePagination && (
        <CardFooter>
          <Pagination
            title={title}
            currentPage={currentPage}
            totalPages={totalPages}
            pageSize={pageSize}
            totalEntries={totalEntries}
            setPageSize={handlePageSize}
            handlePagination={handlePagination}
          />
        </CardFooter>
      )}
    </Card>
  );
};

export default Results;
