import { registerRootComponent } from 'expo';
import { enableScreens } from 'react-native-screens';

enableScreens();

import App from './src/App.jsx';

registerRootComponent(App);
