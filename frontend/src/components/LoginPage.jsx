import React, { useState } from 'react';
import { 
  Lock, 
  Mail, 
  ArrowRight, 
  KeyRound, 
  Sparkles, 
  ShieldCheck, 
  AlertCircle, 
  CheckCircle2, 
  Info, 
  Copy, 
  Check,
  Flame,
  Code2
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

export default function LoginPage({ onBypassDemo }) {
  const { 
    login, 
    register, 
    loginWithGoogle, 
    resetPassword, 
    authError, 
    setAuthError, 
    isFirebaseConfigured,
    jwtToken,
    currentUser
  } = useAuth();
  const { addToast } = useToast();

  const [mode, setMode] = useState('login'); // 'login' | 'register' | 'reset'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resetSent, setResetSent] = useState(false);
  const [showConfigHelper, setShowConfigHelper] = useState(!isFirebaseConfigured);
  const [copiedKey, setCopiedKey] = useState(false);

  // Submit Handler
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) {
      addToast('Please enter your email address', 'error');
      return;
    }

    if (mode !== 'reset' && !password) {
      addToast('Please enter your password', 'error');
      return;
    }

    if (mode === 'register' && password !== confirmPassword) {
      addToast('Passwords do not match', 'error');
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === 'login') {
        await login(email, password);
        addToast('Signed in successfully', 'success');
      } else if (mode === 'register') {
        await register(email, password);
        addToast('Account created & authenticated!', 'success');
      } else if (mode === 'reset') {
        await resetPassword(email);
        setResetSent(true);
        addToast('Password reset link sent to your email', 'info');
      }
    } catch (err) {
      const msg = err.message.replace('Firebase: ', '').replace(/\(auth\/[^)]+\)\.?/, '').trim();
      addToast(msg || 'Authentication failed', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Google Login Handler
  const handleGoogleLogin = async () => {
    setIsSubmitting(true);
    try {
      await loginWithGoogle();
      addToast('Google Sign-in successful', 'success');
    } catch (err) {
      const msg = err.message.replace('Firebase: ', '').replace(/\(auth\/[^)]+\)\.?/, '').trim();
      addToast(msg || 'Google Sign-in failed', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyEnvSample = () => {
    const text = `VITE_FIREBASE_API_KEY=AIzaSy...
VITE_FIREBASE_AUTH_DOMAIN=your-app.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-app.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456:web:abcd1234`;
    navigator.clipboard.writeText(text);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
    addToast('.env template copied to clipboard', 'info');
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        
        {/* Minimal Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-600 mb-2">
            <Flame className="w-6 h-6 text-amber-600 fill-amber-500/20" />
          </div>
          
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 font-display">
            {mode === 'login' && 'Sign in to your account'}
            {mode === 'register' && 'Create your account'}
            {mode === 'reset' && 'Reset your password'}
          </h1>
          
          <p className="text-sm text-slate-500">
            {mode === 'login' && 'Enter your credentials to access the extraction workspace'}
            {mode === 'register' && 'Enter your details to generate your Firebase JWT session'}
            {mode === 'reset' && "We'll send you a password recovery link"}
          </p>
        </div>

        {/* Minimal Card Shell */}
        <div className="bg-white/90 backdrop-blur-sm border border-brand-border rounded-2xl p-6 sm:p-8 shadow-warm-md relative">
          
          {/* Top Status / Notice */}
          {!isFirebaseConfigured && (
            <div className="mb-6 p-3.5 rounded-xl bg-amber-50 border border-amber-200/80 text-amber-900 text-xs">
              <div className="flex items-start gap-2.5">
                <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <div className="flex-1 space-y-1">
                  <p className="font-semibold text-amber-950">Firebase Config Pending</p>
                  <p className="text-[11px] leading-relaxed text-amber-800">
                    Add your Firebase keys to <code className="bg-amber-100/80 px-1 py-0.5 rounded font-mono text-[10px]">frontend/.env</code> to enable live authentication.
                  </p>
                  <button
                    type="button"
                    onClick={() => setShowConfigHelper(!showConfigHelper)}
                    className="text-[11px] font-bold text-amber-900 underline hover:text-amber-950 mt-1 inline-block"
                  >
                    {showConfigHelper ? 'Hide setup instructions' : 'View quick setup guide →'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Config Helper Drawer */}
          {showConfigHelper && (
            <div className="mb-6 p-4 rounded-xl bg-slate-900 text-slate-200 text-xs font-mono border border-slate-800 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <span className="text-[11px] text-amber-400 font-bold flex items-center gap-1.5">
                  <Code2 className="w-3.5 h-3.5" /> frontend/.env template
                </span>
                <button
                  type="button"
                  onClick={copyEnvSample}
                  className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-200 px-2 py-0.5 rounded bg-slate-800 border border-slate-700 transition-colors"
                >
                  {copiedKey ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  {copiedKey ? 'Copied' : 'Copy'}
                </button>
              </div>

              <pre className="text-[10px] text-slate-300 leading-relaxed overflow-x-auto whitespace-pre-wrap">
{`VITE_FIREBASE_API_KEY=AIzaSy...
VITE_FIREBASE_AUTH_DOMAIN=your-app.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-app.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456:web:abcd1234`}
              </pre>

              <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px]">
                <span className="text-slate-400 font-sans">Want to explore UI without keys?</span>
                {onBypassDemo && (
                  <button
                    type="button"
                    onClick={onBypassDemo}
                    className="font-sans font-semibold text-amber-400 hover:text-amber-300 underline"
                  >
                    Continue in Demo Mode →
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Auth Error Banner */}
          {authError && (
            <div className="mb-5 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              <span className="flex-1 text-[11px] font-medium">{authError}</span>
            </div>
          )}

          {/* Success Message for Reset */}
          {mode === 'reset' && resetSent && (
            <div className="mb-5 p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs space-y-2">
              <div className="flex items-center gap-2 font-semibold text-emerald-950">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Reset Email Dispatched</span>
              </div>
              <p className="text-[11px] text-emerald-800">
                Check <strong className="text-emerald-950">{email}</strong> for instructions to reset your password.
              </p>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            
            {/* Email Field */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-700 tracking-wide uppercase font-mono">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full pl-9 pr-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 rounded-xl text-sm text-slate-900 placeholder-slate-400 transition-all font-sans"
                />
              </div>
            </div>

            {/* Password Field (for Login / Register) */}
            {mode !== 'reset' && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-semibold text-slate-700 tracking-wide uppercase font-mono">
                    Password
                  </label>
                  {mode === 'login' && (
                    <button
                      type="button"
                      onClick={() => {
                        setMode('reset');
                        setAuthError(null);
                      }}
                      className="text-[11px] text-slate-500 hover:text-amber-700 font-medium transition-colors"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 rounded-xl text-sm text-slate-900 placeholder-slate-400 transition-all font-sans"
                  />
                </div>
              </div>
            )}

            {/* Confirm Password Field (for Register) */}
            {mode === 'register' && (
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-slate-700 tracking-wide uppercase font-mono">
                  Confirm Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <KeyRound className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 rounded-xl text-sm text-slate-900 placeholder-slate-400 transition-all font-sans"
                  />
                </div>
              </div>
            )}

            {/* Primary Action Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white font-semibold text-sm rounded-xl transition-all shadow-sm flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed group cursor-pointer"
            >
              {isSubmitting ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <span>
                    {mode === 'login' && 'Sign In'}
                    {mode === 'register' && 'Create Account'}
                    {mode === 'reset' && 'Send Reset Link'}
                  </span>
                  <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </button>
          </form>

          {/* Social / Alternative Divider */}
          {mode !== 'reset' && (
            <>
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-200" />
                </div>
                <div className="relative flex justify-center text-[10px] uppercase font-mono">
                  <span className="bg-white px-2 text-slate-400 font-bold">Or continue with</span>
                </div>
              </div>

              {/* Google Sign In */}
              <button
                type="button"
                onClick={handleGoogleLogin}
                disabled={isSubmitting}
                className="w-full py-2.5 px-4 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-semibold text-xs rounded-xl transition-all shadow-2xs flex items-center justify-center gap-2.5 cursor-pointer disabled:opacity-50"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>Google Single Sign-On</span>
              </button>
            </>
          )}

          {/* Mode Switchers */}
          <div className="mt-6 pt-4 border-t border-slate-100 text-center text-xs text-slate-500 font-sans">
            {mode === 'login' && (
              <p>
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('register');
                    setAuthError(null);
                  }}
                  className="font-bold text-amber-700 hover:text-amber-800 underline ml-1"
                >
                  Create one now
                </button>
              </p>
            )}

            {mode === 'register' && (
              <p>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('login');
                    setAuthError(null);
                  }}
                  className="font-bold text-amber-700 hover:text-amber-800 underline ml-1"
                >
                  Sign in
                </button>
              </p>
            )}

            {mode === 'reset' && (
              <p>
                Remembered your password?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('login');
                    setAuthError(null);
                  }}
                  className="font-bold text-amber-700 hover:text-amber-800 underline ml-1"
                >
                  Back to Sign In
                </button>
              </p>
            )}
          </div>
        </div>

        {/* Minimal Footer Badges */}
        <div className="flex items-center justify-center gap-4 text-[11px] text-slate-600 font-mono">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" /> Firebase JWT Auth
          </span>
          <span className="text-slate-300">•</span>
          <span>RS256 Verified</span>
        </div>

      </div>
    </div>
  );
}
