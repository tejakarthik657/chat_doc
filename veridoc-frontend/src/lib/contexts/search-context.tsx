"use client";

import React, { createContext, useContext, useState } from 'react';

interface SearchContextType {
    searchQuery: string;
    setSearchQuery: (query: string) => void;
    mobileNavOpen: boolean;
    setMobileNavOpen: (open: boolean) => void;
    toggleMobileNav: () => void;
}

const SearchContext = createContext<SearchContextType | undefined>(undefined);

export function SearchProvider({ children }: { children: React.ReactNode }) {
    const [searchQuery, setSearchQuery] = useState("");
    const [mobileNavOpen, setMobileNavOpen] = useState(false);

    const toggleMobileNav = () => setMobileNavOpen((prev) => !prev);

    return (
        <SearchContext.Provider
            value={{
                searchQuery,
                setSearchQuery,
                mobileNavOpen,
                setMobileNavOpen,
                toggleMobileNav,
            }}
        >
            {children}
        </SearchContext.Provider>
    );
}

export function useSearch() {
    const context = useContext(SearchContext);
    if (context === undefined) {
        throw new Error('useSearch must be used within a SearchProvider');
    }
    return context;
}

export const useDashboardUI = useSearch;

