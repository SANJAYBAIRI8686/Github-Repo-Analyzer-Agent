type CitationLinkProps = {
  repositoryId: number;
  filePath: string;
  lineStart?: number | null;
  lineEnd?: number | null;
};

export function CitationLink({ repositoryId, filePath, lineStart, lineEnd }: CitationLinkProps) {
  const href = `/repos/${repositoryId}/files/${encodeURIComponent(filePath)}?start=${lineStart ?? 1}&end=${lineEnd ?? lineStart ?? 1}`;
  return (
    <a className="rounded-full border border-accent/30 bg-accent/10 px-2.5 py-1 text-xs text-accent2 hover:bg-accent/20" href={href}>
      {filePath}:{lineStart ?? "?"}-{lineEnd ?? "?"}
    </a>
  );
}