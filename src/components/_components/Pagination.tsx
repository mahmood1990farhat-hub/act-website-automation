import React from "react";

type PaginationProps = {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  locale: string;
};

function getPaginationRange(
  current: number,
  total: number
): (number | string)[] {
  const delta = 2;
  const range: (number | string)[] = [];
  const rangeWithDots: (number | string)[] = [];

  for (let i = 1; i <= total; i++) {
    if (
      i === 1 ||
      i === total ||
      (i >= current - delta && i <= current + delta)
    ) {
      range.push(i);
    }
  }

  let lastPage: number | null = null;
  for (let page of range) {
    if (lastPage !== null && typeof page === "number") {
      if (page - lastPage > 1) {
        rangeWithDots.push("...");
      }
    }
    rangeWithDots.push(page);
    if (typeof page === "number") lastPage = page;
  }

  return rangeWithDots;
}


const translations = {
  ar: {
    prev: "السابق",
    next: "التالي",
  },
  en: {
    prev: "Previous",
    next: "Next",
  },
};

const Pagination: React.FC<PaginationProps> = ({
  locale,
  currentPage,
  totalPages,
  onPageChange,
}) => {

  if (totalPages<0) {
    return null
  }
  const pages = getPaginationRange(currentPage, totalPages);
  const t =
    translations[locale as keyof typeof translations] || translations["en"];

  return (
    <div dir="ltr" className="flex items-center justify-center gap-3 py-6 flex-wrap">
      {/* Previous Button */}
      <button
        className="px-4 py-2 rounded-lg bg-foreground/40 border border-muted/20 text-white font-semibold
                   transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed
                   hover:bg-primary hover:text-black hover:border-primary disabled:hover:bg-foreground/40 
                   disabled:hover:text-white"
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
      >
        <span className="flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          <span className="max-sm:hidden">{t.prev}</span>
        </span>
      </button>

      {/* Page Numbers */}
      <div className="flex gap-2 text-sm flex-wrap">
        {pages.map((page, idx) =>
          page === "..." ? (
            <span key={`dots-${idx}`} className="px-3 py-2 text-gray-400 font-medium">
              ...
            </span>
          ) : (
            <button
              key={page}
              onClick={() => onPageChange(page as number)}
              className={`min-w-[40px] px-3 py-2 rounded-lg font-semibold transition-all duration-200 ${
                currentPage === page
                  ? "bg-primary text-black shadow-lg shadow-primary/30 scale-105"
                  : "bg-foreground/40 border border-muted/20 text-gray-300 hover:bg-primary/20 hover:text-primary hover:border-primary/30"
              }`}
            >
              {page}
            </button>
          )
        )}
      </div>

      {/* Next Button */}
      <button
        className="px-4 py-2 rounded-lg bg-foreground/40 border border-muted/20 text-white font-semibold
                   transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed
                   hover:bg-primary hover:text-black hover:border-primary disabled:hover:bg-foreground/40 
                   disabled:hover:text-white"
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
      >
        <span className="flex items-center gap-2">
          <span className="max-sm:hidden">{t.next}</span>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </span>
      </button>
    </div>
  );
};

export default Pagination;
