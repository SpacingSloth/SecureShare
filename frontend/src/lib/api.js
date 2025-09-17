import axios from "axios";
function resolveBaseURL(){try{if(typeof window!=='undefined'&&window.location?.port==='3000'){return "http://localhost:8000"}}catch(_){}const env=process.env.REACT_APP_API_BASE_URL;if(env&&env.trim())return env.trim();return "/api"}
export const api = axios.create({ baseURL: resolveBaseURL() });
api.interceptors.request.use(cfg=>{const t=localStorage.getItem("token");if(t){cfg.headers=cfg.headers||{};cfg.headers.Authorization=`Bearer ${t}`;}return cfg;});
let onUnauthorized=null;export function setOnUnauthorized(h){onUnauthorized=typeof h==="function"?h:null}
api.interceptors.response.use(r=>r,e=>{if(e?.response?.status===401){localStorage.removeItem("token");if(onUnauthorized)onUnauthorized(e);}return Promise.reject(e);});
export default api;