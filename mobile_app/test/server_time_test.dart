import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/core/utils/server_time.dart';

void main() {
  test('naive API timestamps are read as UTC', () {
    final time = parseServerTime('2026-10-11T15:20:53');
    expect(time?.toUtc(), DateTime.utc(2026, 10, 11, 15, 20, 53));
  });

  test('explicit timezone and invalid values are handled', () {
    expect(parseServerTime('2026-10-11T22:20:53+07:00')?.toUtc(),
        DateTime.utc(2026, 10, 11, 15, 20, 53));
    expect(parseServerTime('invalid'), isNull);
  });
}
