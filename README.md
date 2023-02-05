### Buscando o client ID, client secret e tenant ID
Para acessar a API do Microsoft Graph, você precisará de três informações:

- Client ID
- Client Secret
- Tenant ID

#### Client ID
Para obter o client ID, você precisará criar uma aplicação na Azure Active Directory (AAD). Aqui estão os passos para criar uma aplicação:

1. Acesse o portal do Azure e clique no menu Azure Active Directory.
2. Clique em Aplicativos registrados e, em seguida, clique no botão Novo registro de aplicativo.
3. Insira um nome para a sua aplicação e clique em Registrar.
4. Na página de visão geral, clique em Certificados e segredos e, em seguida, clique no botão Novo segredo de cliente.
5. Insira uma descrição para o segredo do cliente e selecione a duração da validade. Em seguida, clique em Adicionar.
6. Copie o `valor do segredo do cliente antes de fechar a janela`, pois não será possível recuperá-lo posteriormente.
7. Na página de visão geral, copie o valor da propriedade `ID do aplicativo (cliente)`. Esse é o seu `client_id`.

#### Client Secret
O `client_secret` foi criado quando você criou um segredo do cliente na seção anterior.

#### Tenant ID
Para obter o tenant ID, você precisará acessar o portal do Azure. Aqui estão os passos para obter o tenant ID:

1. Acesse o portal do Azure e clique no menu Azure Active Directory.
2. Clique em Propriedades.
3. Copie o valor da propriedade `ID do diretório (locatário)`. Esse é o seu `tenant_id`.

Necessário definir as variaveis de ambiente:

```
CLIENT_SECRET= 
CLIENT_ID = 
TENANT_ID = 
```