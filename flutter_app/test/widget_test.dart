import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:nile_one_human/main.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('renders the NILE ONE HUMAN workspace', (tester) async {
    await tester.pumpWidget(const NileOneApp());
    await tester.pump();

    expect(find.text('NILE ONE HUMAN'), findsOneWidget);
    expect(find.text('IMD DAWSA AI'), findsOneWidget);
    expect(find.text('Your next idea starts here'), findsOneWidget);
    expect(find.text('TEST'), findsOneWidget);
  });
}
