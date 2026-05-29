import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { authApi, tokenStore } from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!tokenStore.get()) { setLoading(false); return; }
    authApi.me().then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const r = await authApi.login({ email, password });
    tokenStore.set(r.token);
    setUser(r.user);
    return r.user;
  }, []);
  const register = useCallback(async (data) => {
    const r = await authApi.register(data);
    tokenStore.set(r.token);
    setUser(r.user);
    return r.user;
  }, []);
  const logout = useCallback(() => { tokenStore.clear(); setUser(null); }, []);

  return <AuthCtx.Provider value={{ user, loading, login, register, logout }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);

// ---- Cart store (localStorage of journey_ids + passengers) ----
const CART_KEY = "tc_cart_items";
const CartCtx = createContext(null);

export function CartProvider({ children }) {
  const [items, setItems] = useState(() => {
    try { return JSON.parse(localStorage.getItem(CART_KEY) || "[]"); } catch { return []; }
  });
  useEffect(() => { localStorage.setItem(CART_KEY, JSON.stringify(items)); }, [items]);

  const add = (journey_id, passengers = 1, meta = {}) => {
    setItems((prev) => {
      if (prev.find((i) => i.journey_id === journey_id)) return prev;
      return [...prev, { journey_id, passengers, ...meta }];
    });
  };
  const remove = (journey_id) => setItems((prev) => prev.filter((i) => i.journey_id !== journey_id));
  const setPassengers = (journey_id, p) =>
    setItems((prev) => prev.map((i) => (i.journey_id === journey_id ? { ...i, passengers: p } : i)));
  const clear = () => setItems([]);

  return (
    <CartCtx.Provider value={{ items, add, remove, setPassengers, clear, count: items.length }}>
      {children}
    </CartCtx.Provider>
  );
}
export const useCart = () => useContext(CartCtx);
