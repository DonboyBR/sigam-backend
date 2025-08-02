from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum, DecimalField, IntegerField, Q
from django.db.models.functions import Coalesce, TruncDay
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from .models import Produto, Venda, ItemVenda, Caixa
from .serializers import (
    ProdutoSerializer, VendaSerializer, CaixaSerializer,
    CaixaAberturaSerializer, CaixaHistorySerializer, UserSerializer,
    CaixaUpdateSerializer
)
import json
from datetime import date, timedelta

User = get_user_model()


class IsSuperiorUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff


class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='estoque-baixo')
    def estoque_baixo(self, request):
        produtos_com_estoque_baixo = Produto.objects.filter(estoque__lte=10).order_by('estoque')
        serializer = self.get_serializer(produtos_com_estoque_baixo, many=True)
        return Response(serializer.data)


class VendaViewSet(viewsets.ModelViewSet):
    queryset = Venda.objects.all()
    serializer_class = VendaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        return {'request': self.request}


class CaixaViewSet(viewsets.ModelViewSet):
    queryset = Caixa.objects.all().order_by('-data_abertura')
    serializer_class = CaixaSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='aberto')
    def get_caixa_aberto(self, request):
        try:
            caixa_aberto = Caixa.objects.get(responsavel=request.user, status='ABERTO')
            serializer = self.get_serializer(caixa_aberto)
            return Response(serializer.data)
        except Caixa.DoesNotExist:
            return Response(None, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='aberto/totais')
    def get_totals(self, request):
        try:
            caixa_aberto = Caixa.objects.get(responsavel=request.user, status='ABERTO')
            vendas_no_periodo = Venda.objects.filter(data_venda__gte=caixa_aberto.data_abertura, vendedor=request.user)
            totais = vendas_no_periodo.values('metodo_pagamento').annotate(
                total_metodo=Coalesce(Sum('total'), 0, output_field=DecimalField()))
            resultado = {'dinheiro': 0, 'credito': 0, 'debito': 0, 'pix': 0, 'total': 0}
            for item in totais:
                metodo = item['metodo_pagamento'].lower().replace('cartao de ', '').replace('cartão', 'credito')
                if metodo in resultado:
                    resultado[metodo] = item['total_metodo']
            resultado['total'] = sum(resultado.values())
            return Response(resultado)
        except Caixa.DoesNotExist:
            return Response({'detail': 'Nenhum caixa aberto para este usuário.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='abrir')
    def abrir_caixa(self, request):
        if Caixa.objects.filter(responsavel=request.user, status='ABERTO').exists():
            return Response({'detail': 'Você já possui um caixa aberto.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = CaixaAberturaSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(responsavel=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='fechar')
    def fechar_caixa(self, request, pk=None):
        caixa = self.get_object()
        if caixa.status == 'FECHADO':
            return Response({'detail': 'Este caixa já está fechado.'}, status=status.HTTP_400_BAD_REQUEST)

        vendas_do_caixa = caixa.vendas.all()
        total_sistema = vendas_do_caixa.aggregate(total=Coalesce(Sum('total'), 0, output_field=DecimalField()))['total']
        caixa.valor_fechamento_sistema = total_sistema

        totais_str = request.data.get('totais', '{}')
        totais_apurados = json.loads(totais_str)

        caixa.dinheiro_apurado = totais_apurados.get('dinheiro', 0)
        caixa.credito_apurado = totais_apurados.get('credito', 0)
        caixa.debito_apurado = totais_apurados.get('debito', 0)
        caixa.pix_apurado = totais_apurados.get('pix', 0)
        caixa.valor_fechamento_apurado = totais_apurados.get('total', 0)

        anexo = request.FILES.get('anexo_filipeta')
        if anexo:
            caixa.anexo_filipeta = anexo

        caixa.status = 'FECHADO'
        caixa.data_fechamento = timezone.now()
        caixa.save()
        return Response(self.get_serializer(caixa).data)

    @action(detail=False, methods=['get'], url_path='historico')
    def history(self, request):
        user = request.user
        data_str = request.query_params.get('data')
        vendedor_id_str = request.query_params.get('vendedor_id')
        queryset = Caixa.objects.filter(status='FECHADO').order_by('-data_fechamento')
        if not user.is_staff:
            queryset = queryset.filter(responsavel=user)
        elif vendedor_id_str and vendedor_id_str != 'todos':
            queryset = queryset.filter(responsavel_id=vendedor_id_str)
        if data_str:
            data_selecionada = timezone.datetime.strptime(data_str, '%Y-%m-%d').date()
            queryset = queryset.filter(data_fechamento__date=data_selecionada)
        serializer = CaixaHistorySerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='details')
    def details(self, request, pk=None):
        try:
            caixa = self.get_object()
            user = request.user
            if not user.is_staff and caixa.responsavel != user:
                return Response({'detail': 'Acesso negado.'}, status=status.HTTP_403_FORBIDDEN)
            vendas_do_caixa = caixa.vendas.all()
            sigam_totals_calculated = vendas_do_caixa.aggregate(
                dinheiro=Coalesce(Sum('total', filter=Q(metodo_pagamento='Dinheiro')), 0.0,
                                  output_field=DecimalField()),
                pix=Coalesce(Sum('total', filter=Q(metodo_pagamento='PIX')), 0.0, output_field=DecimalField()),
                cartao=Coalesce(Sum('total', filter=Q(metodo_pagamento='Cartao')), 0.0, output_field=DecimalField())
            )
            dinheiro_final = caixa.dinheiro_sistema_ajustado if caixa.dinheiro_sistema_ajustado is not None else sigam_totals_calculated.get(
                'dinheiro', 0)
            credito_final = caixa.credito_sistema_ajustado if caixa.credito_sistema_ajustado is not None else sigam_totals_calculated.get(
                'cartao', 0)
            debito_final = caixa.debito_sistema_ajustado if caixa.debito_sistema_ajustado is not None else 0
            pix_final = caixa.pix_sistema_ajustado if caixa.pix_sistema_ajustado is not None else sigam_totals_calculated.get(
                'pix', 0)
            total_final = (dinheiro_final or 0) + (credito_final or 0) + (debito_final or 0) + (pix_final or 0)
            sigam_totals = {'dinheiro': dinheiro_final, 'credito': credito_final, 'debito': debito_final,
                            'pix': pix_final, 'total': total_final}
            vendas_serializer = VendaSerializer(vendas_do_caixa, many=True, context={'request': request})
            anexo_url = None
            if caixa.anexo_filipeta:
                anexo_url = request.build_absolute_uri(caixa.anexo_filipeta.url)
            response_data = {
                'id': caixa.id, 'responsavel_nome': caixa.responsavel.username,
                'data_abertura': caixa.data_abertura, 'data_fechamento': caixa.data_fechamento,
                'valor_abertura': caixa.valor_abertura, 'anexo_filipeta': anexo_url,
                'apurado_fechamento': {'dinheiro': caixa.dinheiro_apurado, 'credito': caixa.credito_apurado,
                                       'debito': caixa.debito_apurado, 'pix': caixa.pix_apurado, },
                'calculado_sigam': sigam_totals, 'vendas': vendas_serializer.data
            }
            return Response(response_data)
        except Caixa.DoesNotExist:
            return Response({'detail': 'Caixa não encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['patch'], url_path='edit', permission_classes=[IsSuperiorUser])
    def edit_caixa(self, request, pk=None):
        caixa = self.get_object()
        serializer = CaixaUpdateSerializer(instance=caixa, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(CaixaSerializer(caixa).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DashboardAdminAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        vendedor_id_str = request.query_params.get('vendedor_id')

        today = date.today()
        vendas_do_mes = Venda.objects.filter(data_venda__year=today.year, data_venda__month=today.month)

        vendas_filtradas_para_totais = vendas_do_mes
        if vendedor_id_str and vendedor_id_str != 'todos':
            vendas_filtradas_para_totais = vendas_do_mes.filter(vendedor_id=vendedor_id_str)

        total_produtos_vendidos = ItemVenda.objects.filter(venda__in=vendas_filtradas_para_totais).aggregate(
            total=Coalesce(Sum('quantidade'), 0, output_field=IntegerField()))['total']

        ranking_produtos = ItemVenda.objects.filter(venda__in=vendas_do_mes).values('produto__nome').annotate(
            total_vendido=Sum('quantidade')).order_by('-total_vendido')

        # ▼▼▼ LÓGICA ATUALIZADA E SIMPLIFICADA ▼▼▼
        # O gráfico de vendedores agora mostra SEMPRE os 3 funcionários e o total do mês deles
        ranking_vendedores_data = []
        funcionarios_para_ranking = ['gabrielfk', 'thais', 'joao']
        for username in funcionarios_para_ranking:
            try:
                vendedor = User.objects.get(username=username)
                total_vendido = vendas_do_mes.filter(vendedor=vendedor).aggregate(
                    total=Coalesce(Sum('total'), 0, output_field=DecimalField()))['total']
                ranking_vendedores_data.append({'vendedor__username': username, 'valor_total_vendido': total_vendido})
            except User.DoesNotExist:
                ranking_vendedores_data.append({'vendedor__username': username, 'valor_total_vendido': 0})

        # A lista para o FILTRO continua a mesma, mostrando apenas os vendedores selecionáveis
        vendedores_disponiveis = User.objects.filter(username__in=funcionarios_para_ranking).values('id', 'username')

        data = {
            'total_produtos_vendidos': total_produtos_vendidos,
            'ranking_produtos': list(ranking_produtos),
            'ranking_vendedores': ranking_vendedores_data,
            'vendedores_disponiveis': list(vendedores_disponiveis),
        }
        return Response(data)


class DashboardFuncionarioAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        funcionario = request.user
        data_str = request.query_params.get('data')
        vendas_do_periodo = Venda.objects.filter(vendedor=funcionario)
        if data_str:
            data_selecionada = timezone.datetime.strptime(data_str, '%Y-%m-%d').date()
            inicio_dia = timezone.make_aware(timezone.datetime.combine(data_selecionada, timezone.datetime.min.time()))
            fim_dia = timezone.make_aware(timezone.datetime.combine(data_selecionada, timezone.datetime.max.time()))
            vendas_do_periodo = vendas_do_periodo.filter(data_venda__range=(inicio_dia, fim_dia))
        else:
            try:
                caixa_aberto = Caixa.objects.get(responsavel=funcionario, status='ABERTO')
                vendas_do_periodo = vendas_do_periodo.filter(data_venda__gte=caixa_aberto.data_abertura)
            except Caixa.DoesNotExist:
                vendas_do_periodo = Venda.objects.none()
        total_vendido = vendas_do_periodo.aggregate(total=Coalesce(Sum('total'), 0, output_field=DecimalField()))[
            'total']
        itens_vendidos = ItemVenda.objects.filter(venda__in=vendas_do_periodo)
        produtos_vendidos = itens_vendidos.aggregate(total=Coalesce(Sum('quantidade'), 0, output_field=IntegerField()))[
            'total']
        data = {'totalVendidoTurno': total_vendido, 'produtosVendidosTurno': produtos_vendidos, }
        return Response(data)


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)