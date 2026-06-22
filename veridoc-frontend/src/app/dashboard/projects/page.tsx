"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { projectService, ProjectOut } from "@/services/project.service";
import { Plus, Globe, Database, FileText, Trash2, Loader2, ArrowRight } from "lucide-react";

export default function ProjectsPage() {
    const router = useRouter();
    const [projects, setProjects] = useState<ProjectOut[]>([]);
    const [loading, setLoading] = useState(true);
    const [modalOpen, setModalOpen] = useState(false);
    
    // Modal Form State
    const [name, setName] = useState("");
    const [url, setUrl] = useState("");
    const [maxPages, setMaxPages] = useState(50);
    const [useDynamicCrawl, setUseDynamicCrawl] = useState(false);
    const [sitemapUrl, setSitemapUrl] = useState("");
    const [loginUrl, setLoginUrl] = useState("");
    const [loginUsername, setLoginUsername] = useState("");
    const [loginPassword, setLoginPassword] = useState("");
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [formSubmitting, setFormSubmitting] = useState(false);
    const [error, setError] = useState("");

    const loadProjects = async () => {
        try {
            const data = await projectService.list();
            setProjects(data.projects);
        } catch (err) {
            console.error("Failed to load projects:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadProjects();
        // Poll status every 8 seconds to update crawling status automatically
        const interval = setInterval(loadProjects, 8000);
        return () => clearInterval(interval);
    }, []);

    const handleDelete = async (e: React.MouseEvent, id: string) => {
        e.preventDefault();
        e.stopPropagation();
        if (confirm("Are you sure you want to delete this project? All vector embeddings and crawled data will be permanently deleted.")) {
            try {
                await projectService.delete(id);
                setProjects(projects.filter(p => p.id !== id));
            } catch (err) {
                alert("Failed to delete project");
            }
        }
    };

    const handleCreateProject = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setFormSubmitting(true);

        if (!name.trim() || !url.trim()) {
            setError("Project Name and Website URL are required.");
            setFormSubmitting(false);
            return;
        }

        try {
            const newProject = await projectService.create({
                name: name.trim(),
                website_url: url.trim(),
                max_pages: maxPages,
                use_dynamic_crawl: useDynamicCrawl,
                sitemap_url: sitemapUrl.trim() || undefined,
                login_url: loginUrl.trim() || undefined,
                login_username: loginUsername.trim() || undefined,
                login_password: loginPassword.trim() || undefined
            });
            setModalOpen(false);
            // Reset fields
            setName("");
            setUrl("");
            setMaxPages(50);
            setUseDynamicCrawl(false);
            setSitemapUrl("");
            setLoginUrl("");
            setLoginUsername("");
            setLoginPassword("");
            setShowAdvanced(false);
            // Redirect to project workspace
            router.push(`/dashboard/projects/${newProject.id}`);
        } catch (err: any) {
            const msg = err.response?.data?.detail || "Failed to create project. Please verify the URL.";
            setError(msg);
        } finally {
            setFormSubmitting(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case "active":
            case "ready":
                return "success";
            case "crawling":
                return "info";
            case "indexing":
                return "warning";
            case "error":
                return "destructive";
            default:
                return "secondary";
        }
    };

    return (
        <div className="p-8 max-w-[1600px] mx-auto min-h-[calc(100vh-60px)] space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="font-display text-3xl mb-2">Knowledge Projects</h1>
                    <p className="text-text-muted text-sm">
                        Build customized search agents by crawling external websites and organizational portals.
                    </p>
                </div>
                <Button onClick={() => setModalOpen(true)} className="gap-2 bg-accent hover:bg-accent/80 text-white rounded-none">
                    <Plus size={16} />
                    Create Project
                </Button>
            </div>

            {loading ? (
                <div className="h-[400px] flex items-center justify-center">
                    <div className="flex flex-col items-center gap-3">
                        <Loader2 className="animate-spin text-accent" size={32} />
                        <span className="text-sm font-mono text-text-muted">LOADING PROJECTS...</span>
                    </div>
                </div>
            ) : projects.length === 0 ? (
                <div className="h-[400px] border border-dashed border-border bg-surface/20 flex flex-col items-center justify-center p-8 text-center space-y-6">
                    <div className="p-4 bg-surface-high border border-border inline-block rounded-none text-text-muted">
                        <Globe size={48} />
                    </div>
                    <div className="space-y-2 max-w-md">
                        <h3 className="text-lg font-medium text-text-primary">No Knowledge Projects</h3>
                        <p className="text-sm text-text-muted">
                            Start indexing an organization or documentation website by entering a homepage URL. We'll crawl its web pages and extract PDF reports.
                        </p>
                    </div>
                    <Button onClick={() => setModalOpen(true)} className="bg-accent text-white rounded-none">
                        Create Your First Project
                    </Button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {projects.map((project) => (
                        <Link key={project.id} href={`/dashboard/projects/${project.id}`} className="block group">
                            <Card className="h-full border border-border bg-white/80 backdrop-blur-md hover:bg-white hover:border-accent/40 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-indigo-500/5 flex flex-col justify-between rounded-none relative">
                                <CardHeader className="space-y-2 pb-4">
                                    <div className="flex items-start justify-between">
                                        <Badge variant={getStatusColor(project.status)} className="rounded-none uppercase font-mono text-[10px]">
                                            {project.status}
                                        </Badge>
                                        <button
                                            onClick={(e) => handleDelete(e, project.id)}
                                            className="text-text-muted hover:text-red-400 p-1 hover:bg-surface-high transition-colors"
                                            title="Delete Project"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                    <CardTitle className="text-lg group-hover:text-accent transition-colors truncate">
                                        {project.name}
                                    </CardTitle>
                                    <CardDescription className="flex items-center gap-1.5 text-xs truncate font-mono text-text-muted">
                                        <Globe size={12} />
                                        {project.website_url}
                                    </CardDescription>
                                </CardHeader>
                                
                                <CardContent className="pt-0 space-y-4">
                                    <div className="grid grid-cols-2 gap-4 py-3 border-y border-border/50 text-center font-mono">
                                        <div className="space-y-1">
                                            <div className="text-xs text-text-muted">PAGES CRAWLED</div>
                                            <div className="text-lg font-medium text-text-primary flex items-center justify-center gap-1">
                                                <FileText size={14} className="text-accent" />
                                                {project.pages_crawled}
                                            </div>
                                        </div>
                                        <div className="space-y-1 border-l border-border/50">
                                            <div className="text-xs text-text-muted">DOCUMENTS FOUND</div>
                                            <div className="text-lg font-medium text-text-primary flex items-center justify-center gap-1">
                                                <Database size={14} className="text-accent" />
                                                {project.docs_found}
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div className="flex items-center justify-between text-xs text-text-muted pt-2">
                                        <span>CRAWLED {new Date(project.created_at).toLocaleDateString()}</span>
                                        <span className="flex items-center gap-1 text-accent group-hover:translate-x-1 transition-transform">
                                            Open Workspace
                                            <ArrowRight size={12} />
                                        </span>
                                    </div>
                                </CardContent>
                            </Card>
                        </Link>
                    ))}
                </div>
            )}

            {/* Creation Modal */}
            {modalOpen && (
                <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-surface border border-border w-full max-w-lg p-6 space-y-6 shadow-xl relative animate-in fade-in zoom-in-95 duration-200 rounded-none">
                        <div className="space-y-2">
                            <h2 className="text-xl font-display">Create Knowledge Project</h2>
                            <p className="text-sm text-text-muted">
                                Configure the web spider parameters for indexing the domain's public portals.
                            </p>
                        </div>
                        
                        <form onSubmit={handleCreateProject} className="space-y-4 font-sans">
                            <div className="space-y-2">
                                <label className="text-xs font-mono text-text-muted uppercase">Project Name</label>
                                <Input
                                    placeholder="e.g. KITSW Web Assistant"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="rounded-none border-border focus-visible:ring-accent"
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-mono text-text-muted uppercase">Website Homepage URL</label>
                                <Input
                                    placeholder="https://kitsw.ac.in"
                                    type="url"
                                    value={url}
                                    onChange={(e) => setUrl(e.target.value)}
                                    className="rounded-none border-border focus-visible:ring-accent"
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <div className="flex justify-between items-center text-xs font-mono text-text-muted uppercase">
                                    <span>Crawl Page Limit</span>
                                    <span>{maxPages} pages</span>
                                </div>
                                <input
                                    type="range"
                                    min="10"
                                    max="500"
                                    step="10"
                                    value={maxPages}
                                    onChange={(e) => setMaxPages(parseInt(e.target.value))}
                                    className="w-full accent-accent bg-surface-high cursor-pointer h-1.5 rounded-none"
                                />
                                <span className="text-[10px] text-text-muted block">
                                    Restricts crawl loops. Higher numbers index deeper, but take longer to process.
                                </span>
                            </div>

                            {/* Advanced Settings Toggle */}
                            <div className="border-t border-border pt-4">
                                <button
                                    type="button"
                                    onClick={() => setShowAdvanced(!showAdvanced)}
                                    className="flex items-center justify-between w-full text-xs font-mono text-text-muted hover:text-accent transition-colors uppercase"
                                >
                                    <span>Advanced Crawler & Auth Settings</span>
                                    <span>{showAdvanced ? "[-]" : "[+]"}</span>
                                </button>
                            </div>

                            {showAdvanced && (
                                <div className="space-y-4 pt-2 border-b border-border pb-4 animate-in fade-in slide-in-from-top-2 duration-200">
                                    {/* Playwright Toggle */}
                                    <div className="flex items-center justify-between p-3 bg-surface-high border border-border">
                                        <div className="space-y-0.5">
                                            <label className="text-xs font-mono text-text-primary uppercase cursor-pointer" htmlFor="playwright-toggle">
                                                Enable JS-Enabled Crawling (Playwright)
                                            </label>
                                            <span className="text-[10px] text-text-muted block">
                                                Traverses dynamic menus & JavaScript accordions.
                                            </span>
                                        </div>
                                        <input
                                            id="playwright-toggle"
                                            type="checkbox"
                                            checked={useDynamicCrawl}
                                            onChange={(e) => setUseDynamicCrawl(e.target.checked)}
                                            className="w-4 h-4 accent-accent cursor-pointer"
                                        />
                                    </div>

                                    {/* Sitemap URL */}
                                    <div className="space-y-2">
                                        <label className="text-xs font-mono text-text-muted uppercase">Custom Sitemap URL (Optional)</label>
                                        <Input
                                            placeholder="https://kitsw.ac.in/sitemap.xml"
                                            type="url"
                                            value={sitemapUrl}
                                            onChange={(e) => setSitemapUrl(e.target.value)}
                                            className="rounded-none border-border focus-visible:ring-accent"
                                        />
                                        <span className="text-[10px] text-text-muted block">
                                            Seeds crawl queue with sitemap page list.
                                        </span>
                                    </div>

                                    {/* Portal Authentication Settings */}
                                    <div className="border border-border p-4 bg-surface-high space-y-3">
                                        <div className="text-xs font-mono text-text-primary uppercase border-b border-border pb-2">
                                            Intranet Portal Authentication
                                        </div>
                                        
                                        <div className="space-y-1">
                                            <label className="text-[10px] font-mono text-text-muted uppercase">Login URL</label>
                                            <Input
                                                placeholder="https://portal.kitsw.ac.in/login"
                                                type="url"
                                                value={loginUrl}
                                                onChange={(e) => setLoginUrl(e.target.value)}
                                                className="rounded-none border-border focus-visible:ring-accent h-8 text-sm"
                                            />
                                        </div>

                                        <div className="grid grid-cols-2 gap-3">
                                            <div className="space-y-1">
                                                <label className="text-[10px] font-mono text-text-muted uppercase">Username / Email</label>
                                                <Input
                                                    placeholder="admin@kitsw.ac.in"
                                                    value={loginUsername}
                                                    onChange={(e) => setLoginUsername(e.target.value)}
                                                    className="rounded-none border-border focus-visible:ring-accent h-8 text-sm"
                                                />
                                            </div>
                                            <div className="space-y-1">
                                                <label className="text-[10px] font-mono text-text-muted uppercase">Password</label>
                                                <Input
                                                    placeholder="••••••••"
                                                    type="password"
                                                    value={loginPassword}
                                                    onChange={(e) => setLoginPassword(e.target.value)}
                                                    className="rounded-none border-border focus-visible:ring-accent h-8 text-sm"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {error && (
                                <div className="text-xs text-red-400 font-mono p-3 bg-red-950/20 border border-red-900/30">
                                    {error}
                                </div>
                            )}

                            <div className="flex gap-4 pt-4 justify-end font-mono">
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => setModalOpen(false)}
                                    className="rounded-none border-border hover:bg-surface-high"
                                >
                                    Cancel
                                </Button>
                                <Button
                                    type="submit"
                                    disabled={formSubmitting}
                                    className="rounded-none bg-accent hover:bg-accent/80 text-white gap-2"
                                >
                                    {formSubmitting ? (
                                        <>
                                            <Loader2 className="animate-spin" size={14} />
                                            Initializing...
                                        </>
                                    ) : (
                                        "Start Crawling & Index"
                                    )}
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
