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
        backgroundColor: const Color(0xFF07111F),
        appBar: AppBar(
          backgroundColor: const Color(0xFF07111F),
          surfaceTintColor: Colors.transparent,
          titleSpacing: 18,
          title: Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(13),
                  gradient: const LinearGradient(
                    colors: [Color(0xFF42E8F5), Color(0xFF7864FF)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  boxShadow: [BoxShadow(color: Color(0x6642E8F5), blurRadius: 18)],
                ),
                alignment: Alignment.center,
                child: const Text('N', style: TextStyle(
                  color: Color(0xFF07111F), fontSize: 24, fontWeight: FontWeight.w900)),
              ),
              const SizedBox(width: 11),
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('NILE ONE HUMAN', style: TextStyle(
                    fontSize: 15, fontWeight: FontWeight.w900, letterSpacing: .6)),
                  Text('IMD DAWSA AI', style: TextStyle(
                    fontSize: 10, color: Color(0xFF91A9C7), letterSpacing: 1.4)),
                ],
              ),
            ],
          ),
          actions: [
            IconButton(
              tooltip: 'Backend settings',
              onPressed: _showSettings,
              icon: const Icon(Icons.tune_rounded, color: Color(0xFFB9D3F5)),
            ),
            const SizedBox(width: 6),
          ],
        ),
        body: SafeArea(
          top: false,
          child: Column(
            children: [
              Expanded(
                child: ListView(
                  controller: _scrollController,
                  padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
                  children: [
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(26),
                        gradient: const LinearGradient(
                          colors: [Color(0xFF123C5B), Color(0xFF25224E), Color(0xFF171D38)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        border: Border.all(color: const Color(0xFF3A5578)),
                        boxShadow: const [BoxShadow(
                          color: Color(0x3319CDE8), blurRadius: 24, offset: Offset(0, 10))],
                      ),
                      child: Stack(
                        children: [
                          Positioned(
                            right: -22, top: -26,
                            child: Container(
                              width: 138, height: 138,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(color: const Color(0x3342E8F5), width: 2),
                              ),
                            ),
                          ),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                decoration: BoxDecoration(
                                  color: const Color(0x2242E8F5),
                                  borderRadius: BorderRadius.circular(30),
                                  border: Border.all(color: const Color(0x5542E8F5)),
                                ),
                                child: const Text('YOUR INTELLIGENT WORLD',
                                  style: TextStyle(fontSize: 9, letterSpacing: 1.6,
                                    color: Color(0xFF72EAF5), fontWeight: FontWeight.w800)),
                              ),
                              const SizedBox(height: 16),
                              const Text('One vision.\\nInfinite possibilities.',
                                style: TextStyle(fontSize: 27, height: 1.12,
                                  fontWeight: FontWeight.w900, color: Colors.white)),
                              const SizedBox(height: 10),
                              const Text(
                                'Your AI workspace for ideas, learning and everyday progress.',
                                style: TextStyle(color: Color(0xFFC2D2E7), height: 1.5, fontSize: 13)),
                              const SizedBox(height: 18),
                              Row(
                                children: [
                                  const Icon(Icons.auto_awesome, color: Color(0xFF63E7F2), size: 17),
                                  const SizedBox(width: 7),
                                  Text('Built to grow with you',
                                    style: TextStyle(color: Colors.white.withValues(alpha: .86),
                                      fontSize: 11, fontWeight: FontWeight.w600)),
                                ],
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 17),
                    Row(
                      children: [
                        const Expanded(child: Text('Explore your workspace',
                          style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800))),
                        Text('NILE ONE', style: TextStyle(
                          color: const Color(0xFF6FDDEB).withValues(alpha: .9),
                          fontSize: 10, letterSpacing: 1.2, fontWeight: FontWeight.w800)),
                      ],
                    ),
                    const SizedBox(height: 11),
                    GridView.count(
                      crossAxisCount: 2,
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      mainAxisSpacing: 10,
                      crossAxisSpacing: 10,
                      childAspectRatio: 1.58,
                      children: [
                        _FeatureTile(icon: Icons.auto_awesome_rounded, title: 'NILE AI',
                          subtitle: 'Assistant, models and agents', onTap: () => _showModuleInfo('NILE AI', 'AI assistant, model intelligence, voice, translation, research and agents.'), colors: [Color(0xFF173E5A), Color(0xFF172D49)]),
                        _FeatureTile(icon: Icons.people_alt_rounded, title: 'NILE SOCIAL',
                          subtitle: 'Messages and communities', onTap: () => _showModuleInfo('NILE SOCIAL', 'Social profiles, messaging, communities and creator tools. Backend integration is planned.'), colors: [Color(0xFF34305D), Color(0xFF202746)]),
                        _FeatureTile(icon: Icons.shield_rounded, title: 'NILE SECURITY',
                          subtitle: 'Privacy and protection', onTap: () => _showModuleInfo('NILE SECURITY', 'Security center, account protection and cyber defense integrations.'), colors: [Color(0xFF174B4C), Color(0xFF183A42)]),
                        _FeatureTile(icon: Icons.code_rounded, title: 'NILE DEVELOPER',
                          subtitle: 'Build apps and software', onTap: () => _showModuleInfo('NILE DEVELOPER', 'Developer tools, code workspace, APIs and app creation.'), colors: [Color(0xFF4A3155), Color(0xFF292442)]),
                        _FeatureTile(icon: Icons.cloud_rounded, title: 'NILE CLOUD',
                          subtitle: 'Compute and storage', onTap: () => _showModuleInfo('NILE CLOUD', 'Cloud services, hosting, storage and deployment management.'), colors: [Color(0xFF173E5A), Color(0xFF172D49)]),
                        _FeatureTile(icon: Icons.show_chart_rounded, title: 'NILE TRADING',
                          subtitle: 'Markets and risk tools', onTap: () => _showModuleInfo('NILE TRADING', 'Market research, paper trading and risk analysis. No live trades are enabled.'), colors: [Color(0xFF34305D), Color(0xFF202746)]),
                        _FeatureTile(icon: Icons.account_balance_wallet_rounded, title: 'NILE FINANCE',
                          subtitle: 'Money management', onTap: () => _showModuleInfo('NILE FINANCE', 'Personal finance tools and future licensed payment integrations.'), colors: [Color(0xFF174B4C), Color(0xFF183A42)]),
                        _FeatureTile(icon: Icons.business_center_rounded, title: 'NILE BUSINESS',
                          subtitle: 'Business operations', onTap: () => _showModuleInfo('NILE BUSINESS', 'Business workspace for customers, projects, teams and operations.'), colors: [Color(0xFF4A3155), Color(0xFF292442)]),
                        _FeatureTile(icon: Icons.storefront_rounded, title: 'NILE MARKET',
                          subtitle: 'Products and services', onTap: () => _showModuleInfo('NILE MARKET', 'Marketplace for products, services and digital tools.'), colors: [Color(0xFF173E5A), Color(0xFF172D49)]),
                        _FeatureTile(icon: Icons.movie_creation_rounded, title: 'NILE MEDIA',
                          subtitle: 'Create audio and visuals', onTap: () => _showModuleInfo('NILE MEDIA', 'Creative tools for images, video, audio and content production.'), colors: [Color(0xFF34305D), Color(0xFF202746)]),
                        _FeatureTile(icon: Icons.menu_book_rounded, title: 'NILE KNOWLEDGE',
                          subtitle: 'Learning and research', onTap: () => _showModuleInfo('NILE KNOWLEDGE', 'Learning, research, science and trusted knowledge services.'), colors: [Color(0xFF174B4C), Color(0xFF183A42)]),
                        _FeatureTile(icon: Icons.public_rounded, title: 'NILE FUTURE',
                          subtitle: 'Emerging technologies', onTap: () => _showModuleInfo('NILE FUTURE', 'Long-term research in robotics, energy, industry and advanced technology.'), colors: [Color(0xFF4A3155), Color(0xFF292442)]),
                      ],
                    ),
                    const SizedBox(height: 17),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF101F33),
                        borderRadius: BorderRadius.circular(15),
                        border: Border.all(color: const Color(0xFF263D59)),
                      ),
                      child: Row(
                        children: [
                          Container(width: 9, height: 9, decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: _status.contains('reachable') || _status.contains('received')
                                ? const Color(0xFF52E2AE) : const Color(0xFFFFC36B),
                          )),
                          const SizedBox(width: 9),
                          Expanded(child: Text(_status, maxLines: 2, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 11, color: Color(0xFFB8C9DF)))),
                          TextButton(
                            onPressed: _busy ? null : _checkConnection,
                            child: const Text('TEST', style: TextStyle(
                              color: Color(0xFF69DDEB), fontWeight: FontWeight.w900, fontSize: 11)),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    Row(
                      children: [
                        const Icon(Icons.forum_outlined, color: Color(0xFF68DDEB), size: 19),
                        const SizedBox(width: 8),
                        const Text('Your AI conversation',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
                      ],
                    ),
                    const SizedBox(height: 10),
                    if (_messages.isEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 15),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0D1A2B),
                          borderRadius: BorderRadius.circular(18),
                          border: Border.all(color: const Color(0xFF263D59)),
                        ),
                        child: const Column(
                          children: [
                            Icon(Icons.blur_on_rounded, size: 38, color: Color(0xFF6CDAEB)),
                            SizedBox(height: 10),
                            Text('Your next idea starts here',
                              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                            SizedBox(height: 5),
                            Text('Connect your private AI server, then send your first message.',
                              textAlign: TextAlign.center,
                              style: TextStyle(color: Color(0xFF8FA6C3), fontSize: 12, height: 1.5)),
                          ],
                        ),
                      )
                    else
                      ..._messages.map((message) => Align(
                        alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          constraints: const BoxConstraints(maxWidth: 520),
                          margin: const EdgeInsets.only(bottom: 9),
                          padding: const EdgeInsets.all(13),
                          decoration: BoxDecoration(
                            color: message.isError ? const Color(0xFF482632)
                                : message.isUser ? const Color(0xFF164B70) : const Color(0xFF142237),
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: const Color(0x223D7795)),
                          ),
                          child: SelectableText(message.text,
                            style: const TextStyle(height: 1.5, fontSize: 14)),
                        ),
                      )),
                    if (_busy) const Padding(
                      padding: EdgeInsets.only(top: 8),
                      child: LinearProgressIndicator(minHeight: 2, color: Color(0xFF55DCEB)),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
                decoration: const BoxDecoration(
                  color: Color(0xFF0B1727),
                  border: Border(top: BorderSide(color: Color(0xFF203650))),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _messageController,
                        minLines: 1,
                        maxLines: 4,
                        textInputAction: TextInputAction.send,
                        onSubmitted: (_) => _sendMessage(),
                        decoration: InputDecoration(
                          hintText: 'Message NILE AI…',
                          hintStyle: const TextStyle(color: Color(0xFF8198B5), fontSize: 13),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
                          filled: true,
                          fillColor: const Color(0xFF13243A),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(18),
                            borderSide: const BorderSide(color: Color(0xFF304966))),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(18),
                            borderSide: const BorderSide(color: Color(0xFF304966))),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(18),
                            borderSide: const BorderSide(color: Color(0xFF55DCEB), width: 1.4)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 9),
                    Container(
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        gradient: const LinearGradient(colors: [Color(0xFF52E2ED), Color(0xFF8271FF)]),
                      ),
                      child: IconButton(
                        onPressed: _busy ? null : _sendMessage,
                        icon: const Icon(Icons.arrow_upward_rounded, color: Color(0xFF07111F)),
                        tooltip: 'Send message',
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );


  void _showModuleInfo(String title, String description) {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: const Color(0xFF122238),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w900)),
        content: Text(description, style: const TextStyle(height: 1.5)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('CLOSE'),
          ),
        ],
      ),
    );
  }

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


class _FeatureTile extends StatelessWidget {
  const _FeatureTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.colors,
    this.onTap,
  });
  final IconData icon;
  final String title;
  final String subtitle;
  final List<Color> colors;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(18),
    child: Container(
    padding: const EdgeInsets.all(13),
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(18),
      gradient: LinearGradient(
        colors: colors,
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      ),
      border: Border.all(color: Colors.white.withValues(alpha: .10)),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Icon(icon, color: const Color(0xFF76E7F1), size: 25),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
            const SizedBox(height: 3),
            Text(subtitle, style: const TextStyle(color: Color(0xFFB2C4DB), fontSize: 10)),
          ],
        ),
      ],
    ),
    ),
  );
}

class _ChatMessage {
  const _ChatMessage(this.text, this.isUser, {this.isError = false});
  final String text;
  final bool isUser;
  final bool isError;
}
