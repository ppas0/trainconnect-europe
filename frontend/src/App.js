import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider, CartProvider } from "./store";
import { Header, Footer } from "./components";
import { Home, Search, JourneyDetail, Stations, Cart, CheckoutSuccess, Tickets, AuthPage } from "./pages";

export default function App() {
  return (
    <AuthProvider>
      <CartProvider>
        <BrowserRouter>
          <div className="min-h-screen flex flex-col">
            <Header />
            <main className="flex-1">
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/search" element={<Search />} />
                <Route path="/journey/:id" element={<JourneyDetail />} />
                <Route path="/stations" element={<Stations />} />
                <Route path="/cart" element={<Cart />} />
                <Route path="/checkout/success" element={<CheckoutSuccess />} />
                <Route path="/tickets" element={<Tickets />} />
                <Route path="/login" element={<AuthPage mode="login" />} />
                <Route path="/register" element={<AuthPage mode="register" />} />
                <Route path="*" element={<Home />} />
              </Routes>
            </main>
            <Footer />
          </div>
        </BrowserRouter>
      </CartProvider>
    </AuthProvider>
  );
}
