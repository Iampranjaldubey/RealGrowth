import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

const PageTransition = ({ children }) => {
  const location = useLocation();
  const [displayLocation, setDisplayLocation] = useState(location);
  const [transitionStage, setTransitionStage] = useState('fadeIn');

  useEffect(() => {
    if (location !== displayLocation) {
      setTransitionStage('fadeOut');
    }
  }, [location, displayLocation]);

  return (
    <div
      className={transitionStage === 'fadeIn' ? 'animate-fade-in-up' : ''}
      style={{
        opacity: transitionStage === 'fadeOut' ? 0 : 1,
        transform: transitionStage === 'fadeOut' ? 'translateY(10px)' : 'translateY(0)',
        transition: 'opacity 0.2s ease, transform 0.2s ease',
        minHeight: '100%'
      }}
      onTransitionEnd={() => {
        if (transitionStage === 'fadeOut') {
          setDisplayLocation(location);
          setTransitionStage('fadeIn');
        }
      }}
    >
      {displayLocation === location ? children : null}
    </div>
  );
};

export default PageTransition;
