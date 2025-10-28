import { Input } from "@/components/ui/input";
import {
  type ChangeEvent,
  useEffect,
  useState,
  type Dispatch,
  type SetStateAction,
  useRef,
} from "react";

export interface Account {
  account_id: string;
  account_type: string;
}

interface Props {
  name: string;
  accounts?: Account[]; // unused now, preserved for compatibility
  loading: boolean;
  value: string;
  comp: string;
  setValue: Dispatch<SetStateAction<string>>;
}

const Search = ({
  name,
  accounts = [],
  loading,
  value,
  comp,
  setValue,
}: Props) => {
  const [search, setSearch] = useState("");
  const [exists, setExists] = useState<null | boolean>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState(false);
  const wrapper = useRef<HTMLDivElement | null>(null);

  const handleChange = (e: ChangeEvent) => {
    const val = (e.currentTarget as HTMLInputElement).value ?? "";
    setSearch(val);
    setExists(null);
    setError(false);
  };

  const checkExists = async () => {
    const id = search.trim();
    if (!id) return;
    setChecking(true);
    try {
      const res = await fetch(`/api/accounts/${encodeURIComponent(id)}`, {
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        const ok = Boolean((data as any)?.exists ?? false);
        setExists(ok);
        if (ok) {
          if (comp !== "" && comp === id) {
            setError(true);
            setValue("");
          } else {
            setError(false);
            setValue(id);
          }
        } else {
          setValue("");
        }
      } else {
        setExists(false);
        setValue("");
      }
    } catch {
      setExists(false);
      setValue("");
    } finally {
      setChecking(false);
    }
  };

  const handleClear = () => {
    setSearch("");
    setValue("");
    setExists(null);
    setError(false);
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element;
      if (wrapper.current && !wrapper.current.contains(target)) {
        // noop
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (value === "") setSearch("");
    if (comp === "") setError(false);
  }, [value, comp]);

  return (
    <div className="relative account-dropdown-container" ref={wrapper}>
      <input name={name} type="hidden" value={value} />
      <Input
        required
        type="text"
        placeholder="Search by account ID"
        value={search}
        onChange={handleChange}
        className="w-full"
        disabled={loading}
      />
      {search && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
        >
          ✕
        </button>
      )}
      <div className="mt-2 flex items-center gap-2">
        <button
          type="button"
          onClick={checkExists}
          disabled={loading || !search.trim() || checking}
          className="text-xs px-2 py-1 border rounded"
        >
          {checking ? "Checking..." : "Check"}
        </button>
        {exists === true && !error && (
          <div className="text-xs text-green-600">Account exists</div>
        )}
        {exists === false && (
          <div className="text-xs text-red-600">Account not found</div>
        )}
      </div>
      {value && exists && !error && (
        <div className="text-xs text-green-600 bg-green-50 p-2 rounded absolute w-full">
          ✓ {search}
        </div>
      )}
      {error && (
        <div className="text-xs text-red-600 bg-red-50 p-2 rounded absolute w-full">
          ✕ Accounts must be different
        </div>
      )}
    </div>
  );
};

export default Search;
