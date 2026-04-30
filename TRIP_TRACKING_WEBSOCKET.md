# دليل استخدام WebSocket لتتبع الرحلة (Trip Tracking)

## نظرة عامة

نظام تتبع الرحلة يعتمد على **WebSocket** لمتابعة موقع السائق في الوقت الفعلي. النظام يعمل كالتالي:

- **السائق**: يرسل تحديثات الموقع بشكل دوري بعد الضغط على "On the way" أو أثناء الرحلة النشطة
- **الراكب / لوحة التحكم**: يستقبلون تحديثات الموقع فقط (لا يرسلون)
- **التخزين**: يتم حفظ آخر موقع في Redis فقط (لا يتم حفظ في قاعدة البيانات)
- **التنظيف**: يتم حذف البيانات تلقائياً عند اكتمال أو إلغاء الرحلة

---

## متطلبات الاتصال

### 1. حالة الرحلة

التتبع يعمل فقط عندما تكون حالة الرحلة (`status`) واحدة من:
- `driver_on_the_way` - السائق في الطريق
- `active` - الرحلة نشطة

### 2. المصادقة (Authentication)

في تطبيقات الويب (المتصفح) غالباً لا يمكن إرسال `Authorization` header داخل WebSocket.

لذلك تم اعتماد مصادقة السائق بهذه الطريقة:

- **السائق** بعد فتح الـ WebSocket يرسل أول رسالة `auth` تحتوي `access token` (JWT)
- الخادم يرد بـ `auth_ok` أو `auth_error`
- بعد `auth_ok` فقط يُسمح للسائق بإرسال `location_update`

**ملاحظة:** الراكب/لوحة التحكم يمكنهم الاتصال واستقبال المواقع بدون مصادقة (read-only).

---

## عنوان WebSocket

```
ws://<your-domain>/ws/trips/<trip_id>/tracking/
```

**مثال:**
```
ws://localhost:8000/ws/trips/123/tracking/
ws://api.example.com/ws/trips/456/tracking/
```

---

## الرسائل (Messages)

### 1. رسائل يرسلها السائق (Driver → Server)

#### مصادقة السائق (`auth`) — مطلوبة للويب

أول رسالة يجب أن يرسلها السائق بعد الاتصال (أحد الشكلين التاليين):

```json
{
  "type": "auth",
  "access": "<ACCESS_TOKEN>"
}
```

أو:

```json
{
  "type": "auth",
  "token": "<ACCESS_TOKEN>"
}
```

**رد الخادم:**

```json
{ "type": "auth_ok" }
```

أو:

```json
{ "type": "auth_error" }
```

#### تحديث الموقع (`location_update`)

السائق يرسل هذه الرسالة بشكل دوري (كل 3-5 ثوانٍ مثلاً):

```json
{
  "type": "location_update",
  "lat": 51.5074,
  "lng": -0.1278,
  "heading": 90,    // اختياري: اتجاه السير بالدرجات (0-360)
  "speed": 30        // اختياري: السرعة بالكيلومتر/ساعة
}
```

**الحقول المطلوبة:**
- `type`: يجب أن يكون `"location_update"`
- `lat`: خط العرض (latitude) - **مطلوب**
- `lng`: خط الطول (longitude) - **مطلوب**

**الحقول الاختيارية:**
- `heading`: اتجاه السير بالدرجات (0 = شمال، 90 = شرق، 180 = جنوب، 270 = غرب)
- `speed`: السرعة بالكيلومتر/ساعة

**ملاحظة:** فقط السائق المعيّن للرحلة يمكنه إرسال `location_update`. أي مستخدم آخر سيتم تجاهل رسالته بصمت.

---

### 2. رسائل يستقبلها الجميع (Server → All Clients)

#### تحديث الموقع (`location`)

يستقبلها جميع المتصلين (سائق، راكب، لوحة تحكم) عند وصول تحديث موقع جديد:

```json
{
  "type": "location",
  "location": {
    "lat": 51.5074,
    "lng": -0.1278,
    "heading": 90,
    "speed": 30
  }
}
```

**عند الاتصال:** إذا كان هناك موقع محفوظ مسبقاً في Redis، سيتم إرساله فوراً عند الاتصال.

---

#### انتهاء الرحلة (`ended`)

يتم إرسالها عند اكتمال أو إلغاء الرحلة:

```json
{
  "type": "ended",
  "reason": "completed"  // أو "cancelled" أو "driver_cancelled"
}
```

**القيم المحتملة لـ `reason`:**
- `"completed"`: الرحلة اكتملت
- `"cancelled"`: الرحلة ألغيت من الراكب
- `"driver_cancelled"`: الرحلة ألغيت من السائق

**بعد استقبال هذه الرسالة:** يجب إغلاق الاتصال (close the WebSocket connection).

---

## أمثلة الكود

### مثال 1: تطبيق السائق (Driver App) - JavaScript/TypeScript

```typescript
class TripTrackingService {
  private ws: WebSocket | null = null;
  private tripId: number;
  private locationUpdateInterval: number | null = null;
  private onLocationUpdate?: (location: any) => void;
  private onTripEnded?: (reason: string) => void;

  constructor(tripId: number) {
    this.tripId = tripId;
  }

  /**
   * الاتصال بـ WebSocket وبدء إرسال تحديثات الموقع
   */
  connect(
    baseUrl: string,
    authToken: string,
    onLocationUpdate?: (location: any) => void,
    onTripEnded?: (reason: string) => void
  ) {
    this.onLocationUpdate = onLocationUpdate;
    this.onTripEnded = onTripEnded;

    // بناء عنوان WebSocket
    const wsUrl = `${baseUrl.replace(/^http/, 'ws')}/ws/trips/${this.tripId}/tracking/`;
    
    // إنشاء اتصال WebSocket
    this.ws = new WebSocket(wsUrl);

    // إضافة token في headers (إذا كان المتصفح يدعمه)
    // ملاحظة: بعض المتصفحات لا تدعم headers في WebSocket
    // يمكنك استخدام query parameter بدلاً من ذلك إذا كان الخادم يدعمه

    this.ws.onopen = () => {
      console.log('WebSocket connected for trip tracking');
      
      // بدء إرسال تحديثات الموقع كل 5 ثوانٍ
      this.startLocationUpdates();
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'location') {
          // تحديث موقع جديد
          if (this.onLocationUpdate) {
            this.onLocationUpdate(data.location);
          }
        } else if (data.type === 'ended') {
          // الرحلة انتهت
          this.stopLocationUpdates();
          if (this.onTripEnded) {
            this.onTripEnded(data.reason);
          }
          this.disconnect();
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.stopLocationUpdates();
    };
  }

  /**
   * بدء إرسال تحديثات الموقع بشكل دوري
   */
  private startLocationUpdates() {
    // التحقق من وجود Geolocation API
    if (!navigator.geolocation) {
      console.error('Geolocation is not supported by this browser');
      return;
    }

    // إرسال تحديث فوري
    this.sendLocationUpdate();

    // إرسال تحديثات كل 5 ثوانٍ
    this.locationUpdateInterval = window.setInterval(() => {
      this.sendLocationUpdate();
    }, 5000); // 5 ثوانٍ
  }

  /**
   * إرسال تحديث موقع واحد
   */
  private sendLocationUpdate() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const locationUpdate = {
          type: 'location_update',
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          heading: position.coords.heading || undefined,
          speed: position.coords.speed ? position.coords.speed * 3.6 : undefined, // تحويل من m/s إلى km/h
        };

        this.ws?.send(JSON.stringify(locationUpdate));
      },
      (error) => {
        console.error('Error getting location:', error);
      },
      {
        enableHighAccuracy: true,
        timeout: 5000,
        maximumAge: 0,
      }
    );
  }

  /**
   * إيقاف إرسال تحديثات الموقع
   */
  private stopLocationUpdates() {
    if (this.locationUpdateInterval) {
      clearInterval(this.locationUpdateInterval);
      this.locationUpdateInterval = null;
    }
  }

  /**
   * قطع الاتصال
   */
  disconnect() {
    this.stopLocationUpdates();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// مثال على الاستخدام
const trackingService = new TripTrackingService(123); // trip_id = 123

trackingService.connect(
  'http://localhost:8000',
  'your-auth-token',
  (location) => {
    // تحديث الموقع على الخريطة
    console.log('New location:', location);
    // updateMapMarker(location.lat, location.lng);
  },
  (reason) => {
    // الرحلة انتهت
    console.log('Trip ended:', reason);
    // showTripEndedMessage(reason);
  }
);

// عند إكمال الرحلة أو إلغائها
// trackingService.disconnect();
```

---

### مثال 2: تطبيق الراكب (Passenger App) - React

```tsx
import React, { useEffect, useState, useRef } from 'react';

interface Location {
  lat: number;
  lng: number;
  heading?: number;
  speed?: number;
}

interface TripTrackingProps {
  tripId: number;
  baseUrl: string;
  authToken: string;
  onTripEnded?: (reason: string) => void;
}

const TripTracking: React.FC<TripTrackingProps> = ({
  tripId,
  baseUrl,
  authToken,
  onTripEnded,
}) => {
  const [currentLocation, setCurrentLocation] = useState<Location | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  useEffect(() => {
    const connect = () => {
      const wsUrl = `${baseUrl.replace(/^http/, 'ws')}/ws/trips/${tripId}/tracking/`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('Connected to trip tracking');
        setIsConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'location') {
            setCurrentLocation(data.location);
          } else if (data.type === 'ended') {
            setIsConnected(false);
            if (onTripEnded) {
              onTripEnded(data.reason);
            }
            ws.close();
          }
        } catch (error) {
          console.error('Error parsing message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        
        // محاولة إعادة الاتصال (مع exponential backoff)
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          reconnectAttempts.current++;
          
          reconnectTimeoutRef.current = window.setTimeout(() => {
            console.log(`Reconnecting... (attempt ${reconnectAttempts.current})`);
            connect();
          }, delay);
        } else {
          console.error('Max reconnection attempts reached');
        }
      };

      wsRef.current = ws;
    };

    connect();

    // التنظيف عند unmount
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [tripId, baseUrl, authToken, onTripEnded]);

  return (
    <div>
      {isConnected ? (
        <div>
          <p>✅ متصل بتتبع الرحلة</p>
          {currentLocation && (
            <div>
              <p>الموقع الحالي:</p>
              <p>Lat: {currentLocation.lat}, Lng: {currentLocation.lng}</p>
              {currentLocation.heading && (
                <p>الاتجاه: {currentLocation.heading}°</p>
              )}
              {currentLocation.speed && (
                <p>السرعة: {currentLocation.speed} km/h</p>
              )}
            </div>
          )}
        </div>
      ) : (
        <p>⏳ جاري الاتصال...</p>
      )}
    </div>
  );
};

export default TripTracking;
```

---

### مثال 3: React Native (Expo)

```typescript
import { useEffect, useState, useRef } from 'react';
import * as Location from 'expo-location';

interface TripTrackingHook {
  currentLocation: Location.LocationObject | null;
  isConnected: boolean;
  connect: () => void;
  disconnect: () => void;
}

export const useTripTracking = (
  tripId: number,
  wsUrl: string,
  authToken: string
): TripTrackingHook => {
  const [currentLocation, setCurrentLocation] = useState<Location.LocationObject | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const locationSubscriptionRef = useRef<Location.LocationSubscription | null>(null);

  const connect = async () => {
    // طلب صلاحيات الموقع
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      console.error('Location permission denied');
      return;
    }

    const fullWsUrl = `${wsUrl}/ws/trips/${tripId}/tracking/`;
    const ws = new WebSocket(fullWsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      
      // بدء تتبع الموقع
      locationSubscriptionRef.current = Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          timeInterval: 5000, // كل 5 ثوانٍ
          distanceInterval: 10, // كل 10 أمتار
        },
        (location) => {
          // إرسال تحديث الموقع
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(
              JSON.stringify({
                type: 'location_update',
                lat: location.coords.latitude,
                lng: location.coords.longitude,
                heading: location.coords.heading || undefined,
                speed: location.coords.speed ? location.coords.speed * 3.6 : undefined,
              })
            );
          }
        }
      );
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'location') {
          // تحديث الموقع المستلم
          setCurrentLocation({
            coords: {
              latitude: data.location.lat,
              longitude: data.location.lng,
              heading: data.location.heading,
              speed: data.location.speed ? data.location.speed / 3.6 : null,
            },
            timestamp: Date.now(),
          });
        } else if (data.type === 'ended') {
          disconnect();
        }
      } catch (error) {
        console.error('Error parsing message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    wsRef.current = ws;
  };

  const disconnect = () => {
    if (locationSubscriptionRef.current) {
      locationSubscriptionRef.current.remove();
      locationSubscriptionRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  };

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, []);

  return {
    currentLocation,
    isConnected,
    connect,
    disconnect,
  };
};
```

---

## معالجة الأخطاء وإعادة الاتصال

### 1. إعادة الاتصال التلقائي (Auto Reconnect)

يُنصح بتنفيذ آلية إعادة اتصال تلقائية مع **exponential backoff**:

```typescript
class WebSocketReconnect {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxAttempts = 5;
  private reconnectTimeout: number | null = null;

  connect(wsUrl: string) {
    this.ws = new WebSocket(wsUrl);

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxAttempts) {
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        this.reconnectAttempts++;
        
        this.reconnectTimeout = window.setTimeout(() => {
          console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
          this.connect(wsUrl);
        }, delay);
      }
    };

    this.ws.onopen = () => {
      this.reconnectAttempts = 0; // إعادة تعيين العداد عند نجاح الاتصال
    };
  }
}
```

### 2. معالجة الأخطاء الشائعة

- **الاتصال فشل**: تحقق من أن حالة الرحلة هي `driver_on_the_way` أو `active`
- **الرسالة لم تُرسل**: تأكد من أن `ws.readyState === WebSocket.OPEN`
- **الموقع غير متاح**: تحقق من صلاحيات الموقع في المتصفح/التطبيق

---

## حالات الاستخدام

### 1. السائق يبدأ التتبع

```typescript
// بعد الضغط على "On the way" (status = driver_on_the_way)
const trackingService = new TripTrackingService(tripId);
trackingService.connect(apiUrl, authToken, onLocationUpdate, onTripEnded);
```

### 2. الراكب يتابع الرحلة

```typescript
// عند فتح صفحة متابعة الرحلة
const trackingService = new TripTrackingService(tripId);
trackingService.connect(apiUrl, authToken, onLocationUpdate, onTripEnded);
// لا يرسل location_update (يستقبل فقط)
```

### 3. إيقاف التتبع

```typescript
// عند إكمال الرحلة أو إلغائها
trackingService.disconnect();
```

---

## ملاحظات مهمة

1. **المصادقة**: تأكد من إرسال token المصادقة في headers أو query parameters (حسب ما يدعمه الخادم)

2. **الأداء**: لا ترسل تحديثات الموقع أكثر من مرة كل 3-5 ثوانٍ لتوفير البطارية وعرض النطاق

3. **الخصوصية**: البيانات محفوظة في Redis فقط ولا يتم حفظها في قاعدة البيانات

4. **التنظيف**: يتم حذف البيانات تلقائياً عند انتهاء الرحلة، لكن يُنصح بإغلاق الاتصال يدوياً

5. **الحالات المدعومة**: التتبع يعمل فقط في حالات `driver_on_the_way` و `active`

---

## الدعم الفني

إذا واجهت أي مشاكل، تأكد من:
- حالة الرحلة صحيحة (`driver_on_the_way` أو `active`)
- المستخدم مسجل دخوله وله صلاحيات مناسبة
- WebSocket URL صحيح ويمكن الوصول إليه
- Redis يعمل على الخادم

---

## مثال كامل - HTML/JavaScript

```html
<!DOCTYPE html>
<html>
<head>
    <title>Trip Tracking Example</title>
</head>
<body>
    <div id="status">Disconnected</div>
    <div id="location">No location yet</div>
    <button id="connectBtn">Connect</button>
    <button id="disconnectBtn">Disconnect</button>

    <script>
        let ws = null;
        const tripId = 123; // استبدل برقم الرحلة الفعلي
        const baseUrl = 'ws://localhost:8000';

        document.getElementById('connectBtn').onclick = () => {
            const wsUrl = `${baseUrl}/ws/trips/${tripId}/tracking/`;
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                document.getElementById('status').textContent = 'Connected';
                console.log('Connected');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'location') {
                    document.getElementById('location').textContent = 
                        `Lat: ${data.location.lat}, Lng: ${data.location.lng}`;
                } else if (data.type === 'ended') {
                    document.getElementById('status').textContent = `Trip ended: ${data.reason}`;
                    ws.close();
                }
            };

            ws.onerror = (error) => {
                console.error('Error:', error);
                document.getElementById('status').textContent = 'Error';
            };

            ws.onclose = () => {
                document.getElementById('status').textContent = 'Disconnected';
            };
        };

        document.getElementById('disconnectBtn').onclick = () => {
            if (ws) {
                ws.close();
            }
        };
    </script>
</body>
</html>
```

---

ملاحظة:
السائق يتصل مع الويب سوكيت عندما يقوم بتحويل حالة الرحلة الى driver_on_the_way 
في هذه احالة بتم تسجيل الرحلة ضمن الredis 
والسائق يبدأ يبعت تحديث للموقع يلي هو فيه 
وهون بيحسن الادمن او الراكب انو يراقب السائق ,
بالنسبة للادمن بيتصفح الرحلات و الرحلات يلي بتكون 
driver_on_the or active 
يظهر بجانبها زر تتبع 
Emad Alden 😇😎


