"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
    Bell,
    CheckCheck,
    Database,
    FileText,
    Loader2,
    LogOut,
    Menu,
    RefreshCw,
    Search,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { authService } from "@/services/auth.service";
import { documentService, DocumentOut } from "@/services/document.service";
import { projectService, ProjectOut } from "@/services/project.service";
import { cn } from "@/lib/utils";
import { useSearch } from "@/lib/contexts/search-context";

interface DashboardNotification {
    id: string;
    title: string;
    message: string;
    href: string;
    createdAt: string;
    read: boolean;
}

interface ActivityItem {
    status: string;
    message: string;
    href: string;
}

interface NotificationStore {
    knownActivity: Record<string, string>;
    notifications: DashboardNotification[];
}

const EMPTY_NOTIFICATION_STORE: NotificationStore = {
    knownActivity: {},
    notifications: [],
};

function getActivitySnapshot(
    documents: DocumentOut[],
    projects: ProjectOut[],
): Record<string, ActivityItem> {
    const activity: Record<string, ActivityItem> = {};

    for (const document of documents) {
        activity[`document:${document.id}`] = {
            status: document.status,
            message: document.filename,
            href: document.status === "ready"
                ? `/dashboard/chat/${document.id}`
                : "/dashboard/documents",
        };
    }

    for (const project of projects) {
        activity[`project:${project.id}`] = {
            status: project.status,
            message: project.name,
            href: `/dashboard/projects/${project.id}`,
        };
    }

    return activity;
}

export function TopBar() {
    const router = useRouter();
    const { searchQuery, setSearchQuery, toggleMobileNav } = useSearch();
    const [showNotifications, setShowNotifications] = useState(false);
    const [showSearchResults, setShowSearchResults] = useState(false);
    const [documents, setDocuments] = useState<DocumentOut[]>([]);
    const [projects, setProjects] = useState<ProjectOut[]>([]);
    const [searchLoading, setSearchLoading] = useState(false);
    const [searchError, setSearchError] = useState("");
    const [notifications, setNotifications] = useState<DashboardNotification[]>([]);
    const [notificationsLoading, setNotificationsLoading] = useState(false);
    const [notificationsError, setNotificationsError] = useState("");
    const [notificationRefresh, setNotificationRefresh] = useState(0);
    const notificationStoreRef = useRef<NotificationStore>(EMPTY_NOTIFICATION_STORE);
    const hasInitialSnapshotRef = useRef(false);
    const notificationStorageKeyRef = useRef<string | null>(null);
    const searchContainerRef = useRef<HTMLDivElement>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);
    const trimmedQuery = searchQuery.trim();

    useEffect(() => {
        if (trimmedQuery.length < 2) {
            setDocuments([]);
            setProjects([]);
            setSearchLoading(false);
            setSearchError("");
            return;
        }

        let active = true;
        setSearchLoading(true);
        setSearchError("");

        const timer = setTimeout(() => {
            Promise.all([documentService.list(), projectService.list()])
                .then(([documentList, projectList]) => {
                    if (active) {
                        setDocuments(documentList.documents);
                        setProjects(projectList.projects);
                    }
                })
                .catch((error: unknown) => {
                    console.error("Failed to search dashboard content:", error);
                    if (active) setSearchError("Search is temporarily unavailable. Please try again.");
                })
                .finally(() => {
                    if (active) setSearchLoading(false);
                });
        }, 200);

        return () => {
            active = false;
            clearTimeout(timer);
        };
    }, [trimmedQuery]);

    useEffect(() => {
        let active = true;
        let interval: ReturnType<typeof setInterval> | undefined;

        const refreshNotifications = async (storageKey: string) => {
            if (active) {
                setNotificationsLoading(true);
                setNotificationsError("");
            }

            try {
                const [documentList, projectList] = await Promise.all([
                    documentService.list(),
                    projectService.list(),
                ]);
                if (!active) return;

                const currentActivity = getActivitySnapshot(documentList.documents, projectList.projects);
                const previousStore = notificationStoreRef.current;
                const nextNotifications = [...previousStore.notifications];

                if (hasInitialSnapshotRef.current) {
                    for (const [key, item] of Object.entries(currentActivity)) {
                        const previousStatus = previousStore.knownActivity[key];
                        if (previousStatus === item.status) continue;

                        const kind = key.startsWith("document:") ? "document" : "project";
                        nextNotifications.unshift({
                            id: `${key}:${item.status}:${Date.now()}`,
                            title: previousStatus
                                ? `${kind === "document" ? "Document" : "Project"} ${item.status}`
                                : `${kind === "document" ? "New document" : "New project"}`,
                            message: item.message,
                            href: item.href,
                            createdAt: new Date().toISOString(),
                            read: false,
                        });
                    }
                }

                const nextStore: NotificationStore = {
                    knownActivity: Object.fromEntries(
                        Object.entries(currentActivity).map(([key, item]) => [key, item.status]),
                    ),
                    notifications: nextNotifications.slice(0, 40),
                };
                notificationStoreRef.current = nextStore;
                hasInitialSnapshotRef.current = true;
                setNotifications(nextStore.notifications);
                localStorage.setItem(storageKey, JSON.stringify(nextStore));
            } catch (error) {
                console.error("Failed to load dashboard notifications:", error);
                if (active) setNotificationsError("Could not load activity. Check your connection and try again.");
            } finally {
                if (active) setNotificationsLoading(false);
            }
        };

        const startPolling = async () => {
            try {
                const user = await authService.getMe();
                if (!active) return;

                const storageKey = `threadwell-notifications:${user.id}`;
                notificationStorageKeyRef.current = storageKey;
                const savedStore = localStorage.getItem(storageKey);

                if (savedStore) {
                    try {
                        const parsed = JSON.parse(savedStore) as NotificationStore;
                        if (
                            parsed &&
                            parsed.knownActivity &&
                            typeof parsed.knownActivity === "object" &&
                            Array.isArray(parsed.notifications)
                        ) {
                            notificationStoreRef.current = parsed;
                            hasInitialSnapshotRef.current = true;
                            setNotifications(parsed.notifications);
                        }
                    } catch (error) {
                        console.error("Failed to parse saved notifications:", error);
                    }
                }

                await refreshNotifications(storageKey);
                interval = setInterval(() => {
                    void refreshNotifications(storageKey);
                }, 20000);
            } catch (error) {
                console.error("Failed to initialize dashboard notifications:", error);
                if (active) setNotificationsError("Could not load activity. Check your connection and try again.");
            }
        };

        void startPolling();
        return () => {
            active = false;
            if (interval) clearInterval(interval);
        };
    }, [notificationRefresh]);

    useEffect(() => {
        const handlePointerDown = (event: PointerEvent) => {
            if (!searchContainerRef.current?.contains(event.target as Node)) {
                setShowSearchResults(false);
            }
        };
        const handleShortcut = (event: globalThis.KeyboardEvent) => {
            if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
                event.preventDefault();
                searchInputRef.current?.focus();
                setShowSearchResults(true);
            }
        };
        document.addEventListener("pointerdown", handlePointerDown);
        document.addEventListener("keydown", handleShortcut);
        return () => {
            document.removeEventListener("pointerdown", handlePointerDown);
            document.removeEventListener("keydown", handleShortcut);
        };
    }, []);

    const matchingDocuments = documents
        .filter((document) => document.filename.toLowerCase().includes(trimmedQuery.toLowerCase()))
        .slice(0, 5);
    const matchingProjects = projects
        .filter((project) =>
            project.name.toLowerCase().includes(trimmedQuery.toLowerCase()) ||
            project.website_url.toLowerCase().includes(trimmedQuery.toLowerCase()),
        )
        .slice(0, 5);
    const unreadCount = notifications.filter((notification) => !notification.read).length;

    const openSearchResult = (href: string) => {
        setShowSearchResults(false);
        setSearchQuery("");
        router.push(href);
    };

    const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        const firstDocument = matchingDocuments[0];
        const firstProject = matchingProjects[0];

        if (firstDocument) {
            openSearchResult(firstDocument.status === "ready"
                ? `/dashboard/chat/${firstDocument.id}`
                : "/dashboard/documents");
        } else if (firstProject) {
            openSearchResult(`/dashboard/projects/${firstProject.id}`);
        } else {
            openSearchResult("/dashboard/documents");
        }
    };

    const handleSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
        if (event.key === "Escape") setShowSearchResults(false);
    };

    const saveNotifications = (nextNotifications: DashboardNotification[]) => {
        setNotifications(nextNotifications);
        notificationStoreRef.current = {
            ...notificationStoreRef.current,
            notifications: nextNotifications,
        };

        const storageKey = notificationStorageKeyRef.current;
        if (!storageKey) return;
        try {
            localStorage.setItem(storageKey, JSON.stringify(notificationStoreRef.current));
        } catch (error) {
            console.error("Failed to save notification state:", error);
        }
    };

    const markAllNotificationsRead = () => {
        saveNotifications(notifications.map((notification) => ({ ...notification, read: true })));
    };

    return (
        <header className="h-[60px] border-b border-border bg-background/80 backdrop-blur-md fixed top-0 right-0 left-0 md:left-[240px] z-30 flex items-center px-2.5 sm:px-6 gap-2 sm:gap-4 transition-all duration-300">
            <Button
                variant="ghost"
                size="icon"
                className="md:hidden text-text-secondary hover:text-text-primary h-9 w-9 shrink-0 active:scale-95"
                onClick={toggleMobileNav}
                aria-label="Toggle navigation menu"
            >
                <Menu className="h-5 w-5" />
            </Button>

            <div className="flex-1 max-w-xl relative min-w-0" ref={searchContainerRef}>
                <form role="search" onSubmit={handleSearchSubmit}>
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
                    <Input
                        ref={searchInputRef}
                        placeholder="Search documents and projects..."
                        className="pl-9 h-9 sm:h-10 text-base sm:text-sm bg-surface-high/50 border-transparent focus:bg-surface focus:border-accent"
                        value={searchQuery}
                        onChange={(event) => {
                            setSearchQuery(event.target.value);
                            setShowSearchResults(true);
                        }}
                        onFocus={() => setShowSearchResults(true)}
                        onKeyDown={handleSearchKeyDown}
                        role="combobox"
                        aria-autocomplete="list"
                        aria-expanded={showSearchResults && trimmedQuery.length >= 2}
                        aria-controls="dashboard-search-results"
                        aria-label="Search documents and projects"
                    />
                    <button type="submit" className="sr-only">Search</button>
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 pointer-events-none">
                        <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border border-border bg-surface px-1.5 font-mono text-[10px] font-medium text-text-muted">
                            Ctrl K
                        </kbd>
                    </div>
                </form>

                {showSearchResults && trimmedQuery.length >= 2 && (
                    <div
                        id="dashboard-search-results"
                        role="listbox"
                        aria-label="Search results"
                        className="absolute left-0 right-0 top-full z-50 mt-2 max-h-[min(70vh,28rem)] overflow-y-auto rounded-xl border border-border bg-surface shadow-2xl"
                    >
                        {searchLoading ? (
                            <div className="flex items-center gap-2 px-4 py-5 text-sm text-text-muted">
                                <Loader2 className="h-4 w-4 animate-spin text-accent" />
                                Searching your space…
                            </div>
                        ) : searchError ? (
                            <p role="alert" className="px-4 py-5 text-sm text-text-secondary">{searchError}</p>
                        ) : matchingDocuments.length === 0 && matchingProjects.length === 0 ? (
                            <p className="px-4 py-5 text-sm text-text-muted">
                                No documents or projects match “{trimmedQuery}”.
                            </p>
                        ) : (
                            <>
                                {matchingDocuments.length > 0 && (
                                    <div className="py-2">
                                        <p className="px-4 py-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                                            Documents
                                        </p>
                                        {matchingDocuments.map((document) => (
                                            <button
                                                key={document.id}
                                                type="button"
                                                role="option"
                                                aria-selected="false"
                                                onMouseDown={(event) => event.preventDefault()}
                                                onClick={() => openSearchResult(
                                                    document.status === "ready"
                                                        ? `/dashboard/chat/${document.id}`
                                                        : "/dashboard/documents",
                                                )}
                                                className="flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-surface-high focus-visible:bg-surface-high focus-visible:outline-none"
                                            >
                                                <FileText className="h-4 w-4 shrink-0 text-accent" />
                                                <span className="min-w-0 flex-1 truncate text-sm text-text-primary">{document.filename}</span>
                                                <span className="text-[10px] uppercase text-text-muted">{document.status}</span>
                                            </button>
                                        ))}
                                    </div>
                                )}
                                {matchingProjects.length > 0 && (
                                    <div className="border-t border-border py-2">
                                        <p className="px-4 py-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                                            Knowledge projects
                                        </p>
                                        {matchingProjects.map((project) => (
                                            <button
                                                key={project.id}
                                                type="button"
                                                role="option"
                                                aria-selected="false"
                                                onMouseDown={(event) => event.preventDefault()}
                                                onClick={() => openSearchResult(`/dashboard/projects/${project.id}`)}
                                                className="flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-surface-high focus-visible:bg-surface-high focus-visible:outline-none"
                                            >
                                                <Database className="h-4 w-4 shrink-0 text-accent" />
                                                <span className="min-w-0 flex-1">
                                                    <span className="block truncate text-sm text-text-primary">{project.name}</span>
                                                    <span className="block truncate text-xs text-text-muted">{project.website_url}</span>
                                                </span>
                                                <span className="text-[10px] uppercase text-text-muted">{project.status}</span>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                )}
            </div>

            <div className="ml-auto flex items-center gap-1 sm:gap-3 shrink-0">
                <div className="relative">
                    <Button
                        variant="ghost"
                        size="icon"
                        className={cn(
                            "text-text-secondary hover:text-text-primary relative h-9 w-9 active:scale-95",
                            showNotifications && "bg-surface-high text-text-primary",
                        )}
                        onClick={() => setShowNotifications((show) => !show)}
                        aria-label={unreadCount ? `Notifications, ${unreadCount} unread` : "Notifications"}
                        aria-expanded={showNotifications}
                    >
                        <Bell className="h-4.5 w-4.5 sm:h-5 sm:w-5" />
                        {unreadCount > 0 && (
                            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-accent px-1 text-[9px] font-bold text-white">
                                {unreadCount > 9 ? "9+" : unreadCount}
                            </span>
                        )}
                    </Button>

                    {showNotifications && (
                        <>
                            <div
                                className="fixed inset-0 z-40 bg-slate-950/20 backdrop-blur-2xs sm:hidden"
                                onClick={() => setShowNotifications(false)}
                                aria-label="Close notifications backdrop"
                            />
                            <section
                                aria-label="Notifications"
                                className="fixed sm:absolute right-2 sm:right-0 top-[64px] sm:top-auto sm:mt-2 w-[calc(100vw-1rem)] sm:w-96 max-w-sm bg-surface border border-border shadow-2xl rounded-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200 z-50"
                            >
                                <div className="flex items-center justify-between border-b border-border bg-surface-high/40 px-4 py-3">
                                    <div>
                                        <h3 className="text-sm font-semibold">Activity</h3>
                                        <p className="mt-0.5 text-xs text-text-muted">Document and project updates</p>
                                    </div>
                                    {unreadCount > 0 && (
                                        <button
                                            type="button"
                                            onClick={markAllNotificationsRead}
                                            className="inline-flex items-center gap-1.5 rounded px-2 py-1 text-xs font-medium text-accent hover:bg-surface-high"
                                        >
                                            <CheckCheck className="h-3.5 w-3.5" />
                                            Mark all read
                                        </button>
                                    )}
                                </div>
                                {notificationsError ? (
                                    <div className="px-5 py-8 text-center">
                                        <p role="alert" className="text-sm text-text-secondary">{notificationsError}</p>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="mt-3 gap-2"
                                            onClick={() => setNotificationRefresh((count) => count + 1)}
                                        >
                                            <RefreshCw className="h-3.5 w-3.5" />
                                            Try again
                                        </Button>
                                    </div>
                                ) : notificationsLoading && notifications.length === 0 ? (
                                    <div className="flex items-center justify-center gap-2 px-6 py-10 text-sm text-text-muted">
                                        <Loader2 className="h-4 w-4 animate-spin text-accent" />
                                        Loading activity…
                                    </div>
                                ) : notifications.length === 0 ? (
                                    <div className="px-6 py-10 text-center">
                                        <Bell className="mx-auto mb-3 h-5 w-5 text-accent" />
                                        <p className="text-sm font-medium text-text-primary">No new activity</p>
                                        <p className="mt-1 text-xs text-text-muted">
                                            Updates appear here when documents or projects change status.
                                        </p>
                                    </div>
                                ) : (
                                    <ul className="max-h-[min(65vh,24rem)] overflow-y-auto divide-y divide-border">
                                        {notifications.map((notification) => (
                                            <li key={notification.id}>
                                                <button
                                                    type="button"
                                                    onClick={() => {
                                                        saveNotifications(notifications.map((item) =>
                                                            item.id === notification.id ? { ...item, read: true } : item,
                                                        ));
                                                        setShowNotifications(false);
                                                        router.push(notification.href);
                                                    }}
                                                    className={cn(
                                                        "flex w-full gap-3 px-4 py-3.5 text-left transition-colors hover:bg-surface-high/70",
                                                        !notification.read && "bg-blue-50/60",
                                                    )}
                                                >
                                                    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-high text-accent">
                                                        {notification.id.startsWith("document:")
                                                            ? <FileText className="h-4 w-4" />
                                                            : <Database className="h-4 w-4" />}
                                                    </span>
                                                    <span className="min-w-0 flex-1">
                                                        <span className="flex items-start justify-between gap-2">
                                                            <span className="text-sm font-medium text-text-primary">{notification.title}</span>
                                                            {!notification.read && <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-accent" />}
                                                        </span>
                                                        <span className="mt-0.5 block truncate text-xs text-text-secondary">{notification.message}</span>
                                                        <time className="mt-1 block text-[10px] text-text-muted" dateTime={notification.createdAt}>
                                                            {new Date(notification.createdAt).toLocaleString()}
                                                        </time>
                                                    </span>
                                                </button>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </section>
                        </>
                    )}
                </div>

                <Button
                    variant="ghost"
                    size="icon"
                    className="text-text-secondary hover:text-text-primary h-9 w-9 active:scale-95"
                    onClick={() => authService.logout()}
                    title="Logout"
                    aria-label="Logout"
                >
                    <LogOut className="h-4.5 w-4.5 sm:h-5 sm:w-5" />
                </Button>
            </div>
        </header>
    );
}
