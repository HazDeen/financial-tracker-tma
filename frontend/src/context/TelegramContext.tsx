// frontend/src/context/TelegramContext.tsx
import React, { createContext, useContext, useEffect, useState } from 'react';
import WebApp from '@twa-dev/sdk';

interface TelegramContextType {
  webApp: typeof WebApp | null;
  user: any;
  haptic: {
    light: () => void;
    medium: () => void;
    heavy: () => void;
    success: () => void;
    error: () => void;
  };
}

const TelegramContext = createContext<TelegramContextType>({
  webApp: null,
  user: null,
  haptic: {
    light: () => {},
    medium: () => {},
    heavy: () => {},
    success: () => {},
    error: () => {},
  },
});

export const TelegramProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [webApp, setWebApp] = useState<typeof WebApp | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && WebApp) {
      WebApp.ready();
      WebApp.expand();

      // Управление цветом статус-бара iOS под стиль High-Contrast Minimalism
      try {
        WebApp.setHeaderColor('#000000');
        WebApp.setBackgroundColor('#000000');
      } catch (e) {
        console.warn('TMA Header color API not supported in this version');
      }

      setWebApp(WebApp);
    }
  }, []);

  const haptic = {
    light: () => webApp?.HapticFeedback.impactOccurred('light'),
    medium: () => webApp?.HapticFeedback.impactOccurred('medium'),
    heavy: () => webApp?.HapticFeedback.impactOccurred('heavy'),
    success: () => webApp?.HapticFeedback.notificationOccurred('success'),
    error: () => webApp?.HapticFeedback.notificationOccurred('error'),
  };

  return (
    <TelegramContext.Provider value={{ webApp, user: webApp?.initDataUnsafe?.user, haptic }}>
      {children}
    </TelegramContext.Provider>
  );
};

export const useTelegram = () => useContext(TelegramContext);