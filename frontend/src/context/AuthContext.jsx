import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  auth,
  googleProvider,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  fbSignOut,
  sendPasswordResetEmail,
  onAuthStateChanged,
  getIdToken,
  isFirebaseConfigured
} from '../api/firebase';
import { api } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [jwtToken, setJwtToken] = useState(null);
  const [tokenClaims, setTokenClaims] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Whitelist & Approval State
  const [approvalStatus, setApprovalStatus] = useState('unauthenticated'); // 'approved' | 'pending' | 'unauthenticated'
  const [userRole, setUserRole] = useState('none'); // 'admin' | 'client' | 'unapproved' | 'none'
  const [isCheckingApproval, setIsCheckingApproval] = useState(false);

  // Query Backend Whitelist Status
  const refreshApprovalStatus = async (tokenOverride = null) => {
    setIsCheckingApproval(true);
    try {
      if (tokenOverride) {
        api.setAuthToken(tokenOverride);
      }
      const res = await api.getAuthStatus();
      if (res && res.status) {
        setApprovalStatus(res.status);
        setUserRole(res.role || 'client');
        return res;
      }
    } catch (err) {
      console.warn('Could not verify approval status with backend:', err);
    } finally {
      setIsCheckingApproval(false);
    }
    return null;
  };

  useEffect(() => {
    if (!auth) {
      setLoading(false);
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      setCurrentUser(user);
      if (user) {
        try {
          // Get the Firebase JWT ID Token
          const token = await getIdToken(user);
          const idTokenResult = await user.getIdTokenResult();
          setJwtToken(token);
          setTokenClaims(idTokenResult.claims);

          // Configure API client with JWT Bearer token
          api.setAuthToken(token);

          // Check Whitelist Approval Status
          await refreshApprovalStatus(token);
        } catch (err) {
          console.error('Failed to get Firebase JWT ID token:', err);
          setJwtToken(null);
          setTokenClaims(null);
          api.setAuthToken(null);
          setApprovalStatus('unauthenticated');
          setUserRole('none');
        }
      } else {
        setJwtToken(null);
        setTokenClaims(null);
        api.setAuthToken(null);
        setApprovalStatus('unauthenticated');
        setUserRole('none');
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  // Sign In with Email & Password
  const login = async (email, password) => {
    setAuthError(null);
    try {
      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      const token = await getIdToken(userCredential.user);
      setJwtToken(token);
      api.setAuthToken(token);
      return userCredential.user;
    } catch (err) {
      setAuthError(err.message);
      throw err;
    }
  };

  // Sign Up with Email & Password
  const register = async (email, password) => {
    setAuthError(null);
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      const token = await getIdToken(userCredential.user);
      setJwtToken(token);
      api.setAuthToken(token);
      return userCredential.user;
    } catch (err) {
      setAuthError(err.message);
      throw err;
    }
  };

  // Sign In with Google
  const loginWithGoogle = async () => {
    setAuthError(null);
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const token = await getIdToken(result.user);
      setJwtToken(token);
      api.setAuthToken(token);
      return result.user;
    } catch (err) {
      setAuthError(err.message);
      throw err;
    }
  };

  // Password Reset
  const resetPassword = async (email) => {
    setAuthError(null);
    try {
      await sendPasswordResetEmail(auth, email);
    } catch (err) {
      setAuthError(err.message);
      throw err;
    }
  };

  // Sign Out
  const logout = async () => {
    try {
      await fbSignOut(auth);
      setJwtToken(null);
      setTokenClaims(null);
      api.setAuthToken(null);
    } catch (err) {
      console.error('Logout error:', err);
    }
  };

  // Force Refresh JWT Token
  const getFreshToken = async () => {
    if (auth?.currentUser) {
      const token = await getIdToken(auth.currentUser, true);
      setJwtToken(token);
      api.setAuthToken(token);
      return token;
    }
    return null;
  };

  const value = {
    currentUser,
    jwtToken,
    tokenClaims,
    loading,
    authError,
    setAuthError,
    isFirebaseConfigured,
    approvalStatus,
    userRole,
    isCheckingApproval,
    refreshApprovalStatus,
    login,
    register,
    loginWithGoogle,
    resetPassword,
    logout,
    getFreshToken
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
