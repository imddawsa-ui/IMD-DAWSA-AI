import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

void main() => runApp(const NileOneApp());

class NileOneApp extends StatelessWidget {
  const NileOneApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'NILE ONE HUMAN',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF38BDF8),
            brightness: Brightness.dark,
          ),
          scaffoldBackgroundColor: const Color(0xFF08111F),
          useMaterial3: true,
          inputDecorationTheme: const InputDecorationTheme(
            border: OutlineInputBorder(),
            filled: true,
            fillColor: Color(0xFF111E30),
          ),
        ),
        home: const HomeScreen(),
      );
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _apiController = TextEditingController();
  final _messageController = TextEditingController();
  final _scrollController = ScrollController();
  final List<_ChatMessage> _messages = [];
  bool _busy = false;
  String _status = 'Not connected';

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    _apiController.text =
        prefs.getString('api_base_url') ?? 'http://10.0.2.2:8000';
    if (mounted) setState(() {});
  }

  Future<void> _saveApiUrl() async {
    final value = _apiController.text.trim().replaceAll(RegExp(r'/+$'), '');
    final uri = Uri.tryParse(value);
    if (uri == null || !uri.hasScheme || uri.host.isEmpty) {
      _show('Enter a valid backend URL, including http:// or https://.');
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('api_base_url', value);
    if (mounted) {
      setState(() => _status = 'Backend URL saved');
      _show('Backend address saved.');
    }
  }

  Future<void> _checkConnection() async {
    final base = _apiController.text.trim().replaceAll(RegExp(r'/+$'), '');
    setState(() {
      _busy = true;
      _status = 'Checking backend…';
    });
    try {
      final response = await http
          .get(Uri.parse('$base/api/health'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode != 200) {
        throw Exception('HTTP ${response.statusCode}');
      }
      setState(() => _status = 'Backend reachable');
    } catch (error) {
      setState(() => _status = 'Connection failed: $error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty || _busy) return;
    final base = _apiController.text.trim().replaceAll(RegExp(r'/+$'), '');
    setState(() {
      _messages.add(_ChatMessage(text, true));
      _messageController.clear();
      _busy = true;
      _status = 'Waiting for NILE AI…';
    });
    _scrollToEnd();
    try {
      final response = await http
          .post(
            Uri.parse('$base/api/chat'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'message': text}),
          )
          .timeout(const Duration(seconds: 190));
      final data = jsonDecode(response.body);
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final detail = data is Map ? data['detail'] : null;
        throw Exception(detail ?? 'HTTP ${response.statusCode}');
      }
      if (data is! Map || data['reply'] is! String) {
        throw const FormatException('Unexpected chat response');
      }
      setState(() {
        _messages.add(_ChatMessage(data['reply'] as String, false));
        _status = 'Response received';
      });
    } catch (error) {
      setState(() {
        _messages.add(_ChatMessage('Could not reach the AI service: $error', false,
            isError: true));
        _status = 'Request failed';
      });
    } finally {
      if (mounted) {
        setState(() => _busy = false);
        _scrollToEnd();
      }
    }
  }

  void _scrollToEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _show(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  void dispose() {
    _apiController.dispose();
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
          title: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('NILE ONE HUMAN', style: TextStyle(fontWeight: FontWeight.w800)),
              Text('IMD DAWSA AI', style: TextStyle(fontSize: 11, color: Colors.white60)),
            ],
          ),
          actions: [
            IconButton(
              tooltip: 'Backend settings',
              onPressed: _showSettings,
              icon: const Icon(Icons.tune),
            ),
          ],
        ),
        body: Column(
          children: [
            Container(
              width: double.infinity,
              margin: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                gradient: const LinearGradient(
                  colors: [Color(0xFF123A5A), Color(0xFF182447)],
                ),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Your unified AI workspace',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                  SizedBox(height: 6),
                  Text('Connect to your private NILE backend to start a conversation.',
                      style: TextStyle(color: Colors.white70)),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18),
              child: Row(
                children: [
                  Icon(Icons.circle, size: 9,
                      color: _status.contains('reachable') ||
                              _status.contains('received')
                          ? Colors.greenAccent
                          : Colors.orangeAccent),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_status, style: const TextStyle(fontSize: 12))),
                  TextButton(
                    onPressed: _busy ? null : _checkConnection,
                    child: const Text('Test connection'),
                  ),
                ],
              ),
            ),
            Expanded(
              child: _messages.isEmpty
                  ? const Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.auto_awesome, size: 42, color: Color(0xFF38BDF8)),
                          SizedBox(height: 12),
                          Text('Start a conversation'),
                          SizedBox(height: 4),
                          Text('Your messages will appear here.',
                              style: TextStyle(color: Colors.white54)),
                        ],
                      ),
                    )
                  : ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.all(16),
                      itemCount: _messages.length,
                      itemBuilder: (context, index) {
                        final message = _messages[index];
                        return Align(
                          alignment: message.isUser
                              ? Alignment.centerRight
                              : Alignment.centerLeft,
                          child: Container(
                            constraints: const BoxConstraints(maxWidth: 520),
                            margin: const EdgeInsets.only(bottom: 10),
                            padding: const EdgeInsets.all(13),
                            decoration: BoxDecoration(
                              color: message.isError
                                  ? Colors.red.withValues(alpha: .15)
                                  : message.isUser
                                      ? const Color(0xFF164B70)
                                      : const Color(0xFF142237),
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: SelectableText(message.text),
                          ),
                        );
                      },
                    ),
            ),
            if (_busy) const LinearProgressIndicator(minHeight: 2),
            SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _messageController,
                        minLines: 1,
                        maxLines: 5,
                        textInputAction: TextInputAction.send,
                        onSubmitted: (_) => _sendMessage(),
                        decoration: const InputDecoration(
                          hintText: 'Message NILE AI…',
                          contentPadding: EdgeInsets.symmetric(
                              horizontal: 16, vertical: 13),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton.filled(
                      onPressed: _busy ? null : _sendMessage,
                      icon: const Icon(Icons.send_rounded),
                      tooltip: 'Send message',
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      );

  Future<void> _showSettings() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => Padding(
        padding: EdgeInsets.fromLTRB(
          20, 24, 20, MediaQuery.of(context).viewInsets.bottom + 24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Backend connection',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            const Text('Use your computer LAN address for a physical phone. '
                'The emulator default is http://10.0.2.2:8000.'),
            const SizedBox(height: 14),
            TextField(
              controller: _apiController,
              keyboardType: TextInputType.url,
              decoration: const InputDecoration(
                labelText: 'Backend base URL',
                hintText: 'http://192.168.1.10:8000',
              ),
            ),
            const SizedBox(height: 14),
            FilledButton(
              onPressed: () async {
                await _saveApiUrl();
                if (context.mounted) Navigator.pop(context);
              },
              child: const Text('Save address'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ChatMessage {
  const _ChatMessage(this.text, this.isUser, {this.isError = false});
  final String text;
  final bool isUser;
  final bool isError;
}
