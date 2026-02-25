'use client'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SearchIcon } from 'lucide-react'
import { useRef, useState } from 'react'

interface Props {
    fetchData: (q: string) => void
    placeholder: string
    setCurrentPage: () => void
    minQueryLength?: number
    register?: (api: {
    setQuery: (s: string) => void;
    submit: () => void;
  }) => void
}

export const SearchNoProps = ({ placeholder }: { placeholder: string }) => <Search fetchData={() => {}} placeholder={placeholder} setCurrentPage={() => {}} />

const Search = ({
  fetchData,
  placeholder = "Search",
  setCurrentPage,
  minQueryLength = 1,
  register,
}: Props) => {
  const [query, setQuery] = useState("");
  const debounce = useRef<NodeJS.Timeout | null>(null);
  const valid = query.trim().length >= minQueryLength;

  const handleChange = (q: string) => {
    setQuery(q);
    setCurrentPage();
    if (debounce.current) clearTimeout(debounce.current);
    const trimmed = q.trim();
    if (trimmed.length === 0) {
      fetchData("");
      return;
    }
    debounce.current = setTimeout(() => {
      if (trimmed.length >= minQueryLength) fetchData(q);
    }, 300);
  };

  const submit = () => {
    if (valid) fetchData(query);
  };
  if (register) {
    register({
      setQuery: (s: string) => {
        setQuery(s);
        setCurrentPage();
        if (s.trim().length >= minQueryLength) fetchData(s);
      },
      submit,
    });
  }

  return (
    <div className="flex gap-2 items-center">
      <Input
        onChange={(e) => handleChange(e.currentTarget.value)}
        value={query}
        autoComplete="off"
        data-1p-ignore
        data-bwignore
        data-lpignore="true"
        data-form-type="other"
        name="search"
        type="search"
        placeholder={placeholder}
        className="flex-1"
      />
      <Button onClick={() => valid && fetchData(query)} disabled={!valid}>
        <SearchIcon className="w-4 h-4" />
      </Button>
    </div>
  );
};

export default Search;