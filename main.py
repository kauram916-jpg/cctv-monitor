import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_vlc_player/flutter_vlc_player.dart';
import 'package:http/http.dart' as http; // AI कॉल के लिए
import 'dart:convert'; // JSON और Base64 के लिए
import 'dart:async'; // Timer के लिए
import 'dart:typed_data'; // Uint8List के लिए

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'My Custom CCTV App',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      home: AuthWrapper(),
      debugShowCheckedModeBanner: false,
    );
  }
}

// =======================================================================
// AUTH, REGISTER, LOGIN CLASSES
// =======================================================================

class AuthWrapper extends StatefulWidget {
  @override
  _AuthWrapperState createState() => _AuthWrapperState();
}

class _AuthWrapperState extends State<AuthWrapper> {
  bool _isLoggedIn = false;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _checkLoginStatus();
  }

  _checkLoginStatus() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    setState(() {
      _isLoggedIn = prefs.getBool('isLoggedIn') ?? false;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(body: Center(child: CircularProgressIndicator()));
    } else {
      return _isLoggedIn ? DashboardScreen() : LoginScreen();
    }
  }
}

class RegisterScreen extends StatefulWidget {
  @override
  _RegisterScreenState createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _confirmPasswordController =
      TextEditingController();
  final _formKey = GlobalKey<FormState>();

  _register() async {
    if (_formKey.currentState!.validate()) {
      if (_passwordController.text != _confirmPasswordController.text) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Passwords do not match')));
        return;
      }

      SharedPreferences prefs = await SharedPreferences.getInstance();
      String? existingUser = prefs.getString(_usernameController.text);
      if (existingUser != null) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Username already taken!')));
        return;
      }

      prefs.setString(_usernameController.text, _passwordController.text);

      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Registration Successful!')));
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Register')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              TextFormField(
                controller: _usernameController,
                decoration: InputDecoration(
                    labelText: 'Username',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.person)),
                validator: (value) => value == null || value.isEmpty
                    ? 'Please enter username'
                    : null,
              ),
              SizedBox(height: 15),
              TextFormField(
                controller: _passwordController,
                decoration: InputDecoration(
                    labelText: 'Password',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.lock)),
                obscureText: true,
                validator: (value) => value == null || value.isEmpty
                    ? 'Please enter password'
                    : value.length < 6
                        ? 'Password must be at least 6 chars'
                        : null,
              ),
              SizedBox(height: 15),
              TextFormField(
                controller: _confirmPasswordController,
                decoration: InputDecoration(
                    labelText: 'Confirm Password',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.lock_reset)),
                obscureText: true,
                validator: (value) => value != _passwordController.text
                    ? 'Passwords do not match'
                    : null,
              ),
              SizedBox(height: 30),
              ElevatedButton(
                onPressed: _register,
                child: Text('Register', style: TextStyle(fontSize: 18)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  _login() async {
    if (_formKey.currentState!.validate()) {
      SharedPreferences prefs = await SharedPreferences.getInstance();
      String? savedPassword = prefs.getString(_usernameController.text);

      if (savedPassword == _passwordController.text) {
        prefs.setBool('isLoggedIn', true);
        Navigator.pushReplacement(
            context, MaterialPageRoute(builder: (_) => DashboardScreen()));
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Invalid username or password')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Login')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              TextFormField(
                controller: _usernameController,
                decoration: InputDecoration(
                    labelText: 'Username',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.person)),
                validator: (value) =>
                    value == null || value.isEmpty ? 'Enter username' : null,
              ),
              SizedBox(height: 15),
              TextFormField(
                controller: _passwordController,
                decoration: InputDecoration(
                    labelText: 'Password',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.lock)),
                obscureText: true,
                validator: (value) =>
                    value == null || value.isEmpty ? 'Enter password' : null,
              ),
              SizedBox(height: 30),
              ElevatedButton(
                onPressed: _login,
                child: Text('Login', style: TextStyle(fontSize: 18)),
              ),
              TextButton(
                onPressed: () => Navigator.push(
                    context, MaterialPageRoute(builder: (_) => RegisterScreen())),
                child: Text("Don't have an account? Register"),
              )
            ],
          ),
        ),
      ),
    );
  }
}

// =======================================================================
// Dashboard with Multi RTSP CCTV Grid
// =======================================================================
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  // AI API का एंडपॉइंट (इसे आपके Render पर लाइव URL से बदला गया है)
  static const String _aiApiEndpoint = 'https://cctv-monitor-4.onrender.com/analyze_frame'; 
  
  final List<TextEditingController> _rtspControllers = [
    TextEditingController(text: 'rtsp://wowzaec2demo.streamlock.net/vod/mp4:BigBuckBunny_115k.mp4'),
  ];
  final List<VlcPlayerController> _vlcControllers = [];
  bool _showGrid = false;
  
  // AI स्टेटस को ट्रैक करने के लिए Map (कैमरा इंडेक्स: स्टेटस स्ट्रिंग)
  final Map<int, String> _cameraStatuses = {};
  Timer? _monitoringTimer;
  bool _isProcessingFrame = false; // ओवरलोड से बचने के लिए

  void _addRTSPField() {
    setState(() {
      _rtspControllers.add(TextEditingController());
    });
  }

  void _startStreams() {
    // पुराने कंट्रोल्स और स्टेटस को साफ़ करें
    for (var c in _vlcControllers) { c.dispose(); }
    _monitoringTimer?.cancel();
    
    _vlcControllers.clear();
    _cameraStatuses.clear();
    
    int index = 0;
    for (var controller in _rtspControllers) {
      final url = controller.text.trim();
      if (url.isNotEmpty) {
        _vlcControllers.add(VlcPlayerController.network(
          url,
          autoInitialize: true,
          autoPlay: true,
        ));
        _cameraStatuses[index] = 'Initializing...';
        index++;
      }
    }
    
    setState(() {
      _showGrid = true;
    });

    // AI मॉनिटरिंग टाइमर शुरू करें
    _startMonitoring();
  }

  void _startMonitoring() {
    _monitoringTimer?.cancel();
    // हर 5 सेकंड में सभी कैमरों को मॉनिटर करें
    _monitoringTimer = Timer.periodic(Duration(seconds: 5), (timer) {
      // एक-एक करके सभी कैमरों को मॉनिटर करने के लिए लूप करें
      for (int i = 0; i < _vlcControllers.length; i++) {
        // AI कॉल को ओवरलैप करने से बचने के लिए, हम सिर्फ एक बार में एक को प्रोसेस कर सकते हैं, 
        // लेकिन अगर API कॉल तेज़ है तो सभी को एक साथ भेजना भी ठीक है।
        // यहाँ हमने `_isProcessingFrame` को हटाकर, इसे प्रति-कैमरा async operation बनाते हैं, 
        // लेकिन ध्यान रखें कि यह एक साथ कई API कॉल भेज सकता है।
        _captureFrameAndSendToAI(_vlcControllers[i], i);
      }
    });
  }

  /**
   * 🤖 महत्वपूर्ण सुधार:
   * VlcPlayerController.takeSnapshot() अब एक File ऑब्जेक्ट नहीं, 
   * बल्कि सीधे एक Uint8List? (बाइट्स का array) लौटाता है।
   * इसलिए, हमें readAsBytes() को हटाना होगा।
   */
  Future<void> _captureFrameAndSendToAI(VlcPlayerController controller, int index) async {
    // कंट्रोलर इनिशियलाइज़ होना चाहिए और AI एंडपॉइंट सेट होना चाहिए
    // ध्यान दें: हमने यहाँ API not set चेक को हटा दिया है क्योंकि अब यह लाइव URL है।
    if (!controller.value.isInitialized) {
      return;
    }

    // प्रोसेसिंग स्टेटस सेट करें
    setState(() {
      // _isProcessingFrame को हटाने से, यह सुनिश्चित करता है कि हर कैमरा अलग से प्रोसेस हो
      _cameraStatuses[index] = 'Processing...'; 
    });

    try {
      // ✅ FIX: अब यह सीधे Uint8List? लौटाएगा
      final Uint8List? capturedBytes = await controller.takeSnapshot();
      
      if (capturedBytes != null) {
        // ✅ FIX: सीधे Uint8List को Base64 में Encode करें
        String base64Image = base64Encode(capturedBytes);

        // API Call
        // Note: Backend expects Form Data (columns) NOT JSON Body for analyze_frame.
        // We MUST change the request type to form data.
        final response = await http.post(
            Uri.parse(_aiApiEndpoint),
            body: {
                'image': base64Image,
                'camera_id': 'cam_$index',
            }
        );
        
        // AI का जवाब Process करें
        if (response.statusCode == 200) {
          final result = jsonDecode(response.body);
          
          setState(() {
            // मान लीजिए AI 'alert_status' key में स्टेटस भेजता है
            _cameraStatuses[index] = result['alert_status'] ?? 'No data';
          });
        } else {
          setState(() {
            _cameraStatuses[index] = 'AI Error (${response.statusCode})';
          });
        }
      } else {
        setState(() {
          _cameraStatuses[index] = 'Snapshot Failed';
        });
      }
    } catch (e) {
      // नेटवर्क या JSON parsing त्रुटियों को पकड़ें
      setState(() {
        _cameraStatuses[index] = 'Network/Client Error';
        print('Error processing camera $index: $e'); // कंसोल में लॉग करें
      });
    }
    // Note: यहाँ _isProcessingFrame को 'finally' में सेट नहीं किया गया है 
    // क्योंकि हमने उसे प्रति-कैमरा प्रोसेसिंग से हटा दिया है।
  }


  void _logout() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    prefs.setBool('isLoggedIn', false);
    // डिस्पोज़ और टाइमर को रद्द करें
    _monitoringTimer?.cancel();
    for (var c in _vlcControllers) { c.dispose(); }
    
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => LoginScreen()));
  }

  @override
  void dispose() {
    _monitoringTimer?.cancel();
    for (var c in _vlcControllers) {
      c.dispose();
    }
    for (var c in _rtspControllers) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('CCTV Dashboard'),
        actions: [
          IconButton(onPressed: _logout, icon: Icon(Icons.logout)),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: _showGrid
            ? _buildGridView() // <-- लाइव स्ट्रीम ग्रिड
            : _buildRTSPInputScreen(), // <-- RTSP इनपुट स्क्रीन
      ),
    );
  }
  
  // 💡 RTSP इनपुट स्क्रीन को अलग विजेट में तोड़ दिया गया है
  Widget _buildRTSPInputScreen() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Welcome Message 
        const Padding(
          padding: EdgeInsets.only(top: 10, bottom: 20),
          child: Text(
            'Welcome! Enter CCTV Stream URLs:',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
        ),
        
        // RTSP URL Input Fields (Expanded ListView)
        Expanded(
          child: ListView.builder(
            itemCount: _rtspControllers.length,
            itemBuilder: (context, index) {
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: TextField(
                  controller: _rtspControllers[index],
                  decoration: InputDecoration(
                    labelText: 'Enter RTSP URL ${index + 1}',
                    border: OutlineInputBorder(),
                  ),
                ),
              );
            },
          ),
        ),
        
        // Add More RTSP Button
        ElevatedButton.icon(
          onPressed: _addRTSPField,
          icon: Icon(Icons.add),
          label: Text('Add More RTSP'),
        ),
        
        // Get Videos Button
        SizedBox(height: 10),
        ElevatedButton(
          onPressed: _startStreams,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.green,
            padding: EdgeInsets.symmetric(horizontal: 30, vertical: 15),
          ),
          child: Text('Get CCTV Videos'),
        ),
        SizedBox(height: 20),
      ],
    );
  }


  // 🤖 AI स्टेटस के साथ ग्रिड व्यू
  Widget _buildGridView() {
    int crossAxisCount = _vlcControllers.length <= 2
        ? 1
        : _vlcControllers.length <= 4
            ? 2
            : 3;

    return GridView.builder(
      itemCount: _vlcControllers.length,
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
      ),
      itemBuilder: (context, index) {
        String status = _cameraStatuses[index] ?? 'Offline';
        Color borderColor = Colors.transparent;
        
        // AI स्टेटस के आधार पर बॉर्डर कलर सेट करें
        if (status.contains('ALERT') || status.contains('Error') || status.contains('Failed') || status.contains('Client Error')) {
          borderColor = Colors.red;
        } else if (status.contains('Processing') || status.contains('Initializing') || status.contains('No data')) {
          borderColor = Colors.yellow;
        } else {
          borderColor = Colors.green; // Default: Safe/Connected
        }

        return Container(
          decoration: BoxDecoration(
            border: Border.all(color: borderColor, width: 4), // AI बॉर्डर
            color: Colors.black,
          ),
          child: Stack(
            children: [
              // Vlc Player
              VlcPlayer(
                controller: _vlcControllers[index],
                aspectRatio: 16 / 9,
                placeholder: Center(child: CircularProgressIndicator())),
              
              // AI स्टेटस दिखाने वाला विजेट
              Positioned(
                bottom: 5,
                left: 5,
                child: Container(
                  padding: EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                  decoration: BoxDecoration(
                    color: borderColor.withOpacity(0.8),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    'Cam ${index + 1}: $status',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 11,
                    ),
                  ),
              ),
              ),
            ],
          ),
        );
      },
    );
  }
}
