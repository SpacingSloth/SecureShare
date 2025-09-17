import api from './api';


function absolutize(pathOrUrl) {
  try {
    return new URL(pathOrUrl).href;
  } catch {
    const apiBase = api?.defaults?.baseURL;
    const base = (apiBase && /^https?:\/\//i.test(apiBase))
      ? apiBase
      : window.location.origin; 

    return new URL(pathOrUrl, base).href;
  }
}

export async function ensureShareLink(fileId, { expireDays, maxViews, reuseExisting }) {
  const payload = {
    expire_days: expireDays,
    max_views: maxViews === '' ? null : Number(maxViews),
    reuse_existing: !!reuseExisting,
  };

  const { data } = await api.post(`/share/${fileId}`, payload);

  if (data?.url) return absolutize(data.url);
  if (data?.token) return absolutize(`/s/${data.token}`);
  if (typeof data === 'string') return absolutize(data);

  throw new Error('Share API: unexpected response shape');
}
